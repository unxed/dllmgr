package catalog

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

func sortStrings(s []string) { sort.Strings(s) }

// Dirs are the subdirectories of a catalog that hold entries, one per kind.
var Dirs = []string{"fixes", "variants", "bundles"}

// LoadDir parses every entry under dir/fixes and dir/variants (the files
// named README.md are documentation and are skipped). It reports all
// problems at once and also rejects an id used by two files.
func LoadDir(dir string) ([]Entry, error) {
	var entries []Entry
	var errs []error
	seen := map[string]string{}
	for _, sub := range Dirs {
		files, err := os.ReadDir(filepath.Join(dir, sub))
		if err != nil {
			if sub == "bundles" && os.IsNotExist(err) {
				continue
			}
			errs = append(errs, err)
			continue
		}
		for _, f := range files {
			name := f.Name()
			if f.IsDir() || name == "README.md" || !strings.HasSuffix(name, ".md") {
				if !f.IsDir() && name != "README.md" {
					errs = append(errs, fmt.Errorf("%s: not a catalog entry: entries are .md files", filepath.Join(dir, sub, name)))
				}
				continue
			}
			file := filepath.Join(dir, sub, name)
			data, err := os.ReadFile(file)
			if err != nil {
				errs = append(errs, err)
				continue
			}
			e, err := Parse(file, data)
			if err != nil {
				errs = append(errs, err)
				continue
			}
			e.Path = sub + "/" + name
			if prev, dup := seen[e.ID]; dup {
				errs = append(errs, fmt.Errorf("%s: field \"id\": %q is already used by %s", file, e.ID, prev))
				continue
			}
			seen[e.ID] = e.Path
			entries = append(entries, *e)
		}
	}
	byID := make(map[string]Entry, len(entries))
	for _, entry := range entries {
		byID[entry.ID] = entry
	}
	for _, entry := range entries {
		if entry.Kind != KindBundle {
			continue
		}
		for _, id := range entry.Fixes {
			if fix, ok := byID[id]; !ok || fix.Kind != KindFix {
				errs = append(errs, fmt.Errorf("%s: field \"fixes\": %q does not name a catalog fix", entry.Path, id))
			}
		}
	}
	if len(errs) > 0 {
		return nil, errors.Join(errs...)
	}
	return entries, nil
}

// BuildIndex returns the content of catalog/index.json: a JSON array of the
// entries sorted by id, two-space indented, ending with a newline. The same
// entries always give the same bytes.
func BuildIndex(entries []Entry) ([]byte, error) {
	sorted := make([]Entry, len(entries))
	copy(sorted, entries)
	sort.Slice(sorted, func(i, j int) bool { return sorted[i].ID < sorted[j].ID })
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	if err := enc.Encode(sorted); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}
