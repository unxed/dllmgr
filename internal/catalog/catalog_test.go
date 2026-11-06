package catalog

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

const sha = "4c4e4672a06370e612f9305be7cab7a59c8dd7d8638297b1029831a4d0218295"

const validFix = `---
id: winehq-59609
kind: fix
bug: https://bugs.winehq.org/show_bug.cgi?id=59609
title: "comctl32: example"
dlls: [comctl32, comctl32_v6]
programs: [FSViewer.exe]
wine: [wine-9.0, wine-11.0]
patch: https://example.org/fix.patch
patch_sha256: ` + sha + `
license: LGPL-2.1-or-later
---

Prose is ignored.
`

const validVariant = `---
id: comctl32-wine-11.0
kind: variant
dll: comctl32
provider: wine
version: "11.0"
arch: i386
license: LGPL-2.1-or-later
source: https://gitlab.winehq.org/wine/wine/-/tree/wine-11.0/dlls/comctl32
sha256: ` + sha + `
slot: system
fetch:
  urls: [https://example.org/wine.deb]
  sha256: ` + sha + `
  format: deb
  member: "*/i386-windows/comctl32.dll"
---
`

// without returns text with every line that starts with prefix removed.
func without(text, prefix string) string {
	var out []string
	for _, l := range strings.Split(text, "\n") {
		if !strings.HasPrefix(l, prefix) {
			out = append(out, l)
		}
	}
	return strings.Join(out, "\n")
}

func TestParse(t *testing.T) {
	tests := []struct {
		name    string
		file    string
		content string
		wantErr string // substring of the error; empty means valid
	}{
		{"valid fix", "fixes/winehq-59609.md", validFix, ""},
		{"valid variant", "variants/comctl32-wine-11.0.md", validVariant, ""},
		{"fix: missing title", "fixes/winehq-59609.md", without(validFix, "title:"), `field "title": required`},
		{"fix: missing bug", "fixes/winehq-59609.md", without(validFix, "bug:"), `field "bug": required`},
		{"fix: missing dlls", "fixes/winehq-59609.md", without(validFix, "dlls:"), `field "dlls": required`},
		{"fix: empty dlls", "fixes/winehq-59609.md", strings.Replace(validFix, "dlls: [comctl32, comctl32_v6]", "dlls: []", 1), `field "dlls": required`},
		{"fix: missing patch", "fixes/winehq-59609.md", without(validFix, "patch:"), `field "patch": required`},
		{"fix: missing patch_sha256", "fixes/winehq-59609.md", without(validFix, "patch_sha256:"), `field "patch_sha256": required`},
		{"fix: missing license", "fixes/winehq-59609.md", without(validFix, "license:"), `field "license": required`},
		{"fix: missing id", "fixes/winehq-59609.md", without(validFix, "id:"), `field "id": required`},
		{"fix: missing kind", "fixes/winehq-59609.md", without(validFix, "kind:"), `field "kind": required`},
		{"bad kind", "fixes/winehq-59609.md", strings.Replace(validFix, "kind: fix", "kind: patch", 1), `field "kind": is "patch"`},
		{"kind does not match directory", "variants/winehq-59609.md", validFix, `but the file is in the directory "variants"`},
		{"bad id pattern", "fixes/WineHQ_1.md", strings.Replace(validFix, "id: winehq-59609", "id: WineHQ_1", 1), `field "id": "WineHQ_1" does not match`},
		{"id and file name differ", "fixes/winehq-1.md", validFix, `the id must equal the file name without .md`},
		{"fix id without bug number", "fixes/winehq-abc.md", strings.Replace(validFix, "winehq-59609", "winehq-abc", 1), `<tracker>-<bug number>`},
		{"unknown tracker", "fixes/foo-1.md", strings.Replace(validFix, "winehq-59609", "foo-1", 1), `unknown tracker "foo"`},
		{"bug number differs from id", "fixes/winehq-59609.md", strings.Replace(validFix, "id=59609", "id=1", 1), `is not the winehq bug 59609`},
		{"bad bug url", "fixes/winehq-59609.md", strings.Replace(validFix, "bug: https://bugs.winehq.org/show_bug.cgi?id=59609", "bug: not-a-url", 1), `field "bug"`},
		{"patch over http", "fixes/winehq-59609.md", strings.Replace(validFix, "https://example.org/fix.patch", "http://example.org/fix.patch", 1), `field "patch": "http://example.org/fix.patch" is not an https URL`},
		{"sha too short", "fixes/winehq-59609.md", strings.Replace(validFix, sha, "abc123", 1), `field "patch_sha256": "abc123" is not a sha256`},
		{"sha upper case", "fixes/winehq-59609.md", strings.Replace(validFix, sha, strings.ToUpper(sha), 1), `field "patch_sha256"`},
		{"bad dll name", "fixes/winehq-59609.md", strings.Replace(validFix, "[comctl32, comctl32_v6]", "[comctl32.dll]", 1), `field "dlls": "comctl32.dll"`},
		{"duplicate dll", "fixes/winehq-59609.md", strings.Replace(validFix, "[comctl32, comctl32_v6]", "[comctl32, comctl32]", 1), `"comctl32" is listed twice`},
		{"unknown field", "fixes/winehq-59609.md", strings.Replace(validFix, "license:", "colour: red\nlicense:", 1), `field "colour": unknown field`},
		{"variant field in a fix", "fixes/winehq-59609.md", strings.Replace(validFix, "license:", "dll: comctl32\nlicense:", 1), `field "dll": unknown field`},
		{"dlls wrong type", "fixes/winehq-59609.md", strings.Replace(validFix, "[comctl32, comctl32_v6]", "comctl32", 1), `wrong type`},
		{"no frontmatter", "fixes/winehq-59609.md", "# just prose\n", `must start with a line "---"`},
		{"unclosed frontmatter", "fixes/winehq-59609.md", "---\nid: winehq-59609\n", `not closed`},
		{"invalid yaml", "fixes/winehq-59609.md", "---\nid: [\n---\n", `invalid YAML`},
		{"empty frontmatter", "fixes/winehq-59609.md", "---\n---\n", `frontmatter is empty`},
		{"variant: missing dll", "variants/comctl32-wine-11.0.md", without(validVariant, "dll:"), `field "dll": required`},
		{"variant: missing provider", "variants/comctl32-wine-11.0.md", without(validVariant, "provider:"), `field "provider": required`},
		{"variant: missing version", "variants/comctl32-wine-11.0.md", without(validVariant, "version:"), `field "version": required`},
		{"variant: missing arch", "variants/comctl32-wine-11.0.md", without(validVariant, "arch:"), `field "arch": required`},
		{"variant: missing license", "variants/comctl32-wine-11.0.md", without(validVariant, "license:"), `field "license": required`},
		{"variant: missing source", "variants/comctl32-wine-11.0.md", without(validVariant, "source:"), `field "source": required`},
		{"variant: missing sha256", "variants/comctl32-wine-11.0.md", strings.Replace(validVariant, "sha256: "+sha+"\nslot", "slot", 1), `field "sha256": required`},
		{"variant: id differs from dll-provider-version", "variants/comctl32-wine-10.0.md", strings.Replace(validVariant, "id: comctl32-wine-11.0", "id: comctl32-wine-10.0", 1), `a variant id is <dll>-<provider>-<version>`},
		{"variant: bad slot", "variants/comctl32-wine-11.0.md", strings.Replace(validVariant, "slot: system", "slot: elsewhere", 1), `field "slot"`},
		{"variant: bad fetch format", "variants/comctl32-wine-11.0.md", strings.Replace(validVariant, "format: deb", "format: zip", 1), `field "fetch.format"`},
		{"variant: fetch without member", "variants/comctl32-wine-11.0.md", without(validVariant, "  member:"), `field "fetch.member": required`},
		{"variant: unknown fetch field", "variants/comctl32-wine-11.0.md", strings.Replace(validVariant, "  format: deb", "  format: deb\n  mirror: x", 1), `field "fetch.mirror": unknown field`},
		{"variant: bad fix reference", "variants/comctl32-wine-11.0.md", strings.Replace(validVariant, "slot: system", "slot: system\nfixes: [\"winehq:1\"]", 1), `field "fixes"`},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			e, err := Parse(tt.file, []byte(tt.content))
			if tt.wantErr == "" {
				if err != nil {
					t.Fatalf("unexpected error: %v", err)
				}
				if e == nil || e.ID == "" {
					t.Fatalf("no entry returned")
				}
				return
			}
			if err == nil {
				t.Fatalf("expected an error containing %q, got none", tt.wantErr)
			}
			if !strings.Contains(err.Error(), tt.wantErr) {
				t.Fatalf("error %q does not contain %q", err, tt.wantErr)
			}
			if !strings.Contains(err.Error(), tt.file) {
				t.Fatalf("error %q does not name the file %q", err, tt.file)
			}
		})
	}
}

func TestParseFields(t *testing.T) {
	e, err := Parse("fixes/winehq-59609.md", []byte(validFix))
	if err != nil {
		t.Fatal(err)
	}
	if e.Kind != KindFix || len(e.DLLs) != 2 || e.DLLs[1] != "comctl32_v6" || e.Programs[0] != "FSViewer.exe" || e.PatchSHA != sha {
		t.Fatalf("unexpected entry: %+v", e)
	}
	v, err := Parse("variants/comctl32-wine-11.0.md", []byte(validVariant))
	if err != nil {
		t.Fatal(err)
	}
	if v.Version != "11.0" || v.Fetch == nil || v.Fetch.Format != "deb" {
		t.Fatalf("unexpected variant: %+v", v)
	}
}

func TestParseCRLF(t *testing.T) {
	crlf := strings.ReplaceAll(validFix, "\n", "\r\n")
	if _, err := Parse("fixes/winehq-59609.md", []byte(crlf)); err != nil {
		t.Fatal(err)
	}
}

func TestParseReportsAllProblems(t *testing.T) {
	bad := without(without(validFix, "bug:"), "license:")
	_, err := Parse("fixes/winehq-59609.md", []byte(bad))
	if err == nil || !strings.Contains(err.Error(), `field "bug"`) || !strings.Contains(err.Error(), `field "license"`) {
		t.Fatalf("expected both problems, got %v", err)
	}
}

func writeEntry(t *testing.T, dir, sub, name, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Join(dir, sub), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, sub, name), []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func fixWithID(num string) string {
	s := strings.ReplaceAll(validFix, "winehq-59609", "winehq-"+num)
	return strings.ReplaceAll(s, "id=59609", "id="+num)
}

func TestIndexOrderAndContent(t *testing.T) {
	dir := t.TempDir()
	writeEntry(t, dir, "fixes", "winehq-9.md", fixWithID("9"))
	writeEntry(t, dir, "fixes", "winehq-100.md", fixWithID("100"))
	writeEntry(t, dir, "variants", "comctl32-wine-11.0.md", validVariant)
	writeEntry(t, dir, "variants", "README.md", "# not an entry\n")

	entries, err := LoadDir(dir)
	if err != nil {
		t.Fatal(err)
	}
	data, err := BuildIndex(entries)
	if err != nil {
		t.Fatal(err)
	}
	// Sorted by id as strings: comctl32-..., winehq-100, winehq-9.
	text := string(data)
	i1 := strings.Index(text, `"id": "comctl32-wine-11.0"`)
	i2 := strings.Index(text, `"id": "winehq-100"`)
	i3 := strings.Index(text, `"id": "winehq-9"`)
	if i1 < 0 || i2 < 0 || i3 < 0 || !(i1 < i2 && i2 < i3) {
		t.Fatalf("index is not sorted by id:\n%s", text)
	}
	if !strings.Contains(text, `"path": "fixes/winehq-9.md"`) || !strings.Contains(text, `"path": "variants/comctl32-wine-11.0.md"`) {
		t.Fatalf("index lacks the paths:\n%s", text)
	}
	if !strings.HasSuffix(text, "]\n") {
		t.Fatalf("index must end with a newline")
	}
	// The same entries in another order give the same bytes.
	rev := []Entry{entries[2], entries[1], entries[0]}
	data2, err := BuildIndex(rev)
	if err != nil {
		t.Fatal(err)
	}
	if string(data2) != text {
		t.Fatalf("index depends on input order")
	}
}

func TestLoadDirErrors(t *testing.T) {
	dir := t.TempDir()
	writeEntry(t, dir, "fixes", "winehq-1.md", fixWithID("1"))
	writeEntry(t, dir, "fixes", "winehq-2.md", fixWithID("1")) // id differs from file name
	writeEntry(t, dir, "fixes", "notes.txt", "x")
	writeEntry(t, dir, "variants", "README.md", "x")
	_, err := LoadDir(dir)
	if err == nil {
		t.Fatal("expected errors")
	}
	for _, want := range []string{"winehq-2.md", "the id must equal the file name", "notes.txt"} {
		if !strings.Contains(err.Error(), want) {
			t.Errorf("error does not contain %q:\n%v", want, err)
		}
	}
}

func TestLoadDirMissingSubdir(t *testing.T) {
	if _, err := LoadDir(t.TempDir()); err == nil {
		t.Fatal("expected an error for a directory without fixes/ and variants/")
	}
}

// The real catalog must pass the same check CI runs.
func TestRealCatalog(t *testing.T) {
	entries, err := LoadDir(filepath.Join("..", "..", "catalog"))
	if err != nil {
		t.Fatalf("catalog/ does not pass check:\n%v", err)
	}
	if len(entries) == 0 {
		t.Fatal("catalog/ has no entries")
	}
}
