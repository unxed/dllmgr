package catalog

import (
	"errors"
	"fmt"
	"net/url"
	"path"
	"path/filepath"
	"regexp"
	"strings"

	"gopkg.in/yaml.v3"
)

var (
	idRe     = regexp.MustCompile(`^[a-z0-9]+-[a-z0-9.-]+$`)
	fixIDRe  = regexp.MustCompile(`^([a-z0-9]+)-([0-9]+)$`)
	sha256Re = regexp.MustCompile(`^[a-f0-9]{64}$`)
	nameRe   = regexp.MustCompile(`^[a-z0-9_]+$`)
	verRe    = regexp.MustCompile(`^[a-z0-9][a-z0-9.-]*$`)
	bugIDRe  = regexp.MustCompile(`^[0-9]+$`)
)

var fixFields = set("id", "kind", "title", "bug", "dlls", "programs", "wine",
	"patch", "patch_sha256", "recipe", "binaries", "evidence", "license",
	"authors", "ai_assisted", "funding")

var fixRequired = []string{"title", "bug", "dlls", "patch", "patch_sha256", "license"}

var variantFields = set("id", "kind", "title", "summary", "dll", "file",
	"provider", "version", "arch", "slot", "license", "source", "sha256",
	"fetch", "fixes", "authors")

var variantRequired = []string{"dll", "provider", "version", "arch", "license", "source", "sha256"}

var bundleFields = set("id", "kind", "title", "programs", "wine", "fixes", "application", "profiles")
var bundleRequired = []string{"title", "programs", "fixes"}

var fetchFields = set("urls", "sha256", "format", "member")

var fetchFormats = map[string]bool{"deb": true, "tar.xz": true, "tar.zst": true, "raw": true}

// trackers maps a tracker name (the first part of a fix id) to the check of
// a bug URL against the bug number.
var trackers = map[string]func(u *url.URL, num string) bool{
	"winehq": func(u *url.URL, num string) bool {
		return u.Host == "bugs.winehq.org" && u.Path == "/show_bug.cgi" && u.Query().Get("id") == num
	},
	// dllmgr issues hold fixes that have no upstream bug yet. Move the
	// entry to its upstream id once a WineHQ report exists.
	"dllmgr": func(u *url.URL, num string) bool {
		return u.Scheme == "https" && u.Host == "github.com" && u.Path == "/unxed/dllmgr/issues/"+num && u.RawQuery == ""
	},
}

func set(names ...string) map[string]bool {
	m := make(map[string]bool, len(names))
	for _, n := range names {
		m[n] = true
	}
	return m
}

// Frontmatter returns the YAML block at the start of a Markdown file: the
// text between the first line "---" and the next line "---".
func Frontmatter(data []byte) ([]byte, error) {
	text := strings.ReplaceAll(string(data), "\r\n", "\n")
	text = strings.TrimPrefix(text, "\ufeff")
	if !strings.HasPrefix(text, "---\n") {
		return nil, errors.New("the file must start with a line \"---\" that opens the YAML frontmatter")
	}
	rest := text[len("---\n"):]
	for pos := 0; pos <= len(rest); {
		end := strings.IndexByte(rest[pos:], '\n')
		var line string
		if end < 0 {
			line = rest[pos:]
		} else {
			line = rest[pos : pos+end]
		}
		if strings.TrimRight(line, " \t") == "---" {
			return []byte(rest[:pos]), nil
		}
		if end < 0 {
			break
		}
		pos += end + 1
	}
	return nil, errors.New("the frontmatter is not closed: no second line \"---\"")
}

// Parse reads the frontmatter of one Markdown file and validates it. file is
// the path used in messages; its base name must be "<id>.md", and when its
// parent directory is "fixes" or "variants" the kind must match it. The
// returned error lists every problem found, one per line, each starting with
// the file path. The Entry is returned only when there is no error.
func Parse(file string, data []byte) (*Entry, error) {
	fm, err := Frontmatter(data)
	if err != nil {
		return nil, fmt.Errorf("%s: %v", file, err)
	}
	var raw map[string]any
	if err := yaml.Unmarshal(fm, &raw); err != nil {
		return nil, fmt.Errorf("%s: invalid YAML in the frontmatter: %v", file, err)
	}
	if raw == nil {
		return nil, fmt.Errorf("%s: the frontmatter is empty", file)
	}
	var e Entry
	if err := yaml.Unmarshal(fm, &e); err != nil {
		return nil, fmt.Errorf("%s: a field has the wrong type: %v", file, err)
	}
	v := &validator{file: file, raw: raw}
	v.entry(&e)
	if len(v.errs) > 0 {
		return nil, errors.Join(v.errs...)
	}
	return &e, nil
}

type validator struct {
	file string
	raw  map[string]any
	errs []error
}

func (v *validator) fail(field, format string, args ...any) {
	msg := fmt.Sprintf(format, args...)
	if field == "" {
		v.errs = append(v.errs, fmt.Errorf("%s: %s", v.file, msg))
		return
	}
	v.errs = append(v.errs, fmt.Errorf("%s: field %q: %s", v.file, field, msg))
}

func (v *validator) entry(e *Entry) {
	// Kind first: it decides the allowed and required fields.
	var allowed map[string]bool
	var required []string
	switch e.Kind {
	case KindFix:
		allowed, required = fixFields, fixRequired
	case KindVariant:
		allowed, required = variantFields, variantRequired
	case KindBundle:
		allowed, required = bundleFields, bundleRequired
	case "":
		v.fail("kind", "required; must be %q, %q or %q", KindFix, KindVariant, KindBundle)
	default:
		v.fail("kind", "is %q; must be %q, %q or %q", e.Kind, KindFix, KindVariant, KindBundle)
	}

	v.id(e)

	if allowed != nil {
		for _, k := range sortedKeys(v.raw) {
			if !allowed[k] {
				v.fail(k, "unknown field for kind %q", e.Kind)
			}
		}
		for _, k := range required {
			if _, ok := v.raw[k]; !ok || isEmpty(v.raw[k]) {
				v.fail(k, "required for kind %q", e.Kind)
			}
		}
	}

	if dir := filepath.Base(filepath.Dir(filepath.FromSlash(v.file))); e.Kind != "" {
		if (dir == "fixes" && e.Kind != KindFix) || (dir == "variants" && e.Kind != KindVariant) || (dir == "bundles" && e.Kind != KindBundle) {
			v.fail("kind", "is %q but the file is in the directory %q", e.Kind, dir)
		}
	}

	switch e.Kind {
	case KindFix:
		v.fix(e)
	case KindVariant:
		v.variant(e)
	case KindBundle:
		v.nonEmptyItems("programs", e.Programs)
		v.nonEmptyItems("wine", e.Wine)
		v.bundleProfiles(e)
		seen := map[string]bool{}
		for _, id := range e.Fixes {
			if !fixIDRe.MatchString(id) {
				v.fail("fixes", "%q is not a fix id", id)
			}
			if seen[id] {
				v.fail("fixes", "%q is listed twice", id)
			}
			seen[id] = true
		}
	}
}

func (v *validator) bundleProfiles(e *Entry) {
	if e.Application != "" && !verRe.MatchString(e.Application) {
		v.fail("application", "%q is not a valid application id", e.Application)
	}
	if len(e.Profiles) == 0 {
		return
	}
	if e.Application == "" {
		v.fail("application", "required when profiles are present")
	}
	profiles, ok := v.raw["profiles"].([]any)
	if !ok {
		return
	}
	fields := set("version", "exe_sha256", "wine", "host_arch", "prefix_arch")
	seen := map[[4]string]bool{}
	for i, profile := range e.Profiles {
		if raw, ok := profiles[i].(map[string]any); ok {
			for _, field := range sortedKeys(raw) {
				if !fields[field] {
					v.fail("profiles", "profile %d has unknown field %q", i+1, field)
				}
			}
		}
		if !verRe.MatchString(profile.Version) || !sha256Re.MatchString(profile.ExeSHA256) ||
			!strings.HasPrefix(profile.Wine, "wine-") || !verRe.MatchString(profile.Wine) ||
			!nameRe.MatchString(profile.HostArch) || (profile.PrefixArch != "win32" && profile.PrefixArch != "win64") {
			v.fail("profiles", "profile %d requires a version, executable SHA256, Wine tag, host architecture and win32 or win64 prefix", i+1)
		}
		key := [4]string{profile.ExeSHA256, profile.Wine, profile.HostArch, profile.PrefixArch}
		if seen[key] {
			v.fail("profiles", "profile %d repeats an executable and platform combination", i+1)
		}
		seen[key] = true
	}
}

func (v *validator) id(e *Entry) {
	if e.ID == "" {
		v.fail("id", "required")
		return
	}
	if !idRe.MatchString(e.ID) {
		v.fail("id", "%q does not match %s", e.ID, idRe)
	}
	base := path.Base(filepath.ToSlash(v.file))
	if want := strings.TrimSuffix(base, ".md"); want != e.ID || !strings.HasSuffix(base, ".md") {
		v.fail("id", "is %q but the file name is %q; the id must equal the file name without .md", e.ID, base)
	}
}

func (v *validator) fix(e *Entry) {
	var bugNum, tracker string
	if m := fixIDRe.FindStringSubmatch(e.ID); m == nil {
		if idRe.MatchString(e.ID) {
			v.fail("id", "%q: a fix id is <tracker>-<bug number>, for example winehq-59609", e.ID)
		}
	} else {
		tracker, bugNum = m[1], m[2]
		if _, ok := trackers[tracker]; !ok {
			v.fail("id", "unknown tracker %q; known trackers: %s", tracker, strings.Join(trackerNames(), ", "))
		}
	}
	if u := v.url("bug", e.Bug, false); u != nil && tracker != "" {
		if check, ok := trackers[tracker]; ok && !check(u, bugNum) {
			v.fail("bug", "%q is not the %s bug %s named by the id", e.Bug, tracker, bugNum)
		}
	}
	v.names("dlls", e.DLLs, nameRe)
	v.nonEmptyItems("programs", e.Programs)
	v.nonEmptyItems("wine", e.Wine)
	v.nonEmptyItems("authors", e.Authors)
	v.url("patch", e.Patch, true)
	v.sha("patch_sha256", e.PatchSHA)
	v.url("binaries", e.Binaries, false)
	v.url("evidence", e.Evidence, false)
	v.url("funding", e.Funding, false)
}

func (v *validator) variant(e *Entry) {
	v.pattern("dll", e.DLL, nameRe)
	v.pattern("provider", e.Provider, nameRe)
	v.pattern("version", e.Version, verRe)
	v.pattern("arch", e.Arch, nameRe)
	if e.DLL != "" && e.Provider != "" && e.Version != "" {
		want := strings.ReplaceAll(e.DLL, "_", "-") + "-" + e.Provider + "-" + e.Version
		if e.ID != want {
			v.fail("id", "is %q; a variant id is <dll>-<provider>-<version> (underscores of the dll name written as \"-\"), here %q", e.ID, want)
		}
	}
	v.url("source", e.Source, false)
	v.sha("sha256", e.SHA256)
	if e.Slot != "" && e.Slot != "system" && !strings.HasPrefix(e.Slot, "sxs:") {
		v.fail("slot", "is %q; must be \"system\" or start with \"sxs:\"", e.Slot)
	}
	v.nonEmptyItems("authors", e.Authors)
	for _, f := range e.Fixes {
		if m := fixIDRe.FindStringSubmatch(f); m == nil {
			v.fail("fixes", "%q is not a fix id such as winehq-59609", f)
		}
	}
	if e.Fetch != nil {
		v.fetch(e.Fetch)
	}
}

func (v *validator) fetch(f *Fetch) {
	if m, ok := v.raw["fetch"].(map[string]any); ok {
		for _, k := range sortedKeys(m) {
			if !fetchFields[k] {
				v.fail("fetch."+k, "unknown field")
			}
		}
	}
	if len(f.URLs) == 0 {
		v.fail("fetch.urls", "required: at least one https URL")
	}
	for _, u := range f.URLs {
		v.url("fetch.urls", u, true)
	}
	v.sha("fetch.sha256", f.SHA256)
	switch {
	case f.Format == "":
		v.fail("fetch.format", "required: deb, tar.xz, tar.zst or raw")
	case !fetchFormats[f.Format]:
		v.fail("fetch.format", "is %q; must be deb, tar.xz, tar.zst or raw", f.Format)
	case f.Format != "raw" && f.Member == "":
		v.fail("fetch.member", "required unless format is raw: a glob that matches exactly one archive member")
	}
}

func (v *validator) url(field, s string, httpsOnly bool) *url.URL {
	if s == "" {
		return nil
	}
	u, err := url.Parse(s)
	if err != nil || u.Host == "" || (u.Scheme != "https" && (httpsOnly || u.Scheme != "http")) {
		if httpsOnly {
			v.fail(field, "%q is not an https URL", s)
		} else {
			v.fail(field, "%q is not an http or https URL", s)
		}
		return nil
	}
	return u
}

func (v *validator) sha(field, s string) {
	if s == "" {
		return
	}
	if !sha256Re.MatchString(s) {
		v.fail(field, "%q is not a sha256: 64 lowercase hexadecimal characters", s)
	}
}

func (v *validator) pattern(field, s string, re *regexp.Regexp) {
	if s != "" && !re.MatchString(s) {
		v.fail(field, "%q does not match %s", s, re)
	}
}

func (v *validator) names(field string, items []string, re *regexp.Regexp) {
	seen := map[string]bool{}
	for _, s := range items {
		if !re.MatchString(s) {
			v.fail(field, "%q does not match %s (a module name in lower case, without .dll)", s, re)
		}
		if seen[s] {
			v.fail(field, "%q is listed twice", s)
		}
		seen[s] = true
	}
}

func (v *validator) nonEmptyItems(field string, items []string) {
	for _, s := range items {
		if strings.TrimSpace(s) == "" {
			v.fail(field, "contains an empty item")
		}
	}
}

func isEmpty(x any) bool {
	switch t := x.(type) {
	case nil:
		return true
	case string:
		return strings.TrimSpace(t) == ""
	case []any:
		return len(t) == 0
	case map[string]any:
		return len(t) == 0
	}
	return false
}

func sortedKeys(m map[string]any) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sortStrings(keys)
	return keys
}

func trackerNames() []string {
	names := make([]string, 0, len(trackers))
	for k := range trackers {
		names = append(names, k)
	}
	sortStrings(names)
	return names
}
