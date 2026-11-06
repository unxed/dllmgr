// Package catalog parses, validates and indexes the dllmgr catalog.
//
// One catalog entry is one Markdown file. The file starts with a YAML
// frontmatter block for the client; the prose below it is for people and is
// ignored here. See catalog/README.md for the format.
package catalog

// Entry kinds.
const (
	KindFix     = "fix"
	KindVariant = "variant"
	KindBundle  = "bundle"
)

// Entry is the frontmatter of one catalog file. It is the union of the
// fields of both kinds; Validate decides which fields each kind may use.
// The JSON form of an Entry is one element of catalog/index.json.
type Entry struct {
	// Common.
	ID      string   `yaml:"id" json:"id"`
	Kind    string   `yaml:"kind" json:"kind"`
	Title   string   `yaml:"title,omitempty" json:"title,omitempty"`
	License string   `yaml:"license,omitempty" json:"license,omitempty"`
	Authors []string `yaml:"authors,omitempty" json:"authors,omitempty"`

	// Fix.
	Bug        string   `yaml:"bug,omitempty" json:"bug,omitempty"`
	DLLs       []string `yaml:"dlls,omitempty" json:"dlls,omitempty"`
	Programs   []string `yaml:"programs,omitempty" json:"programs,omitempty"`
	Wine       []string `yaml:"wine,omitempty" json:"wine,omitempty"`
	Patch      string   `yaml:"patch,omitempty" json:"patch,omitempty"`
	PatchSHA   string   `yaml:"patch_sha256,omitempty" json:"patch_sha256,omitempty"`
	Recipe     string   `yaml:"recipe,omitempty" json:"recipe,omitempty"`
	Binaries   string   `yaml:"binaries,omitempty" json:"binaries,omitempty"`
	Evidence   string   `yaml:"evidence,omitempty" json:"evidence,omitempty"`
	AIAssisted *bool    `yaml:"ai_assisted,omitempty" json:"ai_assisted,omitempty"`
	Funding    string   `yaml:"funding,omitempty" json:"funding,omitempty"`

	// Variant.
	Summary  string   `yaml:"summary,omitempty" json:"summary,omitempty"`
	DLL      string   `yaml:"dll,omitempty" json:"dll,omitempty"`
	File     string   `yaml:"file,omitempty" json:"file,omitempty"`
	Provider string   `yaml:"provider,omitempty" json:"provider,omitempty"`
	Version  string   `yaml:"version,omitempty" json:"version,omitempty"`
	Arch     string   `yaml:"arch,omitempty" json:"arch,omitempty"`
	Slot     string   `yaml:"slot,omitempty" json:"slot,omitempty"`
	Source   string   `yaml:"source,omitempty" json:"source,omitempty"`
	SHA256   string   `yaml:"sha256,omitempty" json:"sha256,omitempty"`
	Fetch    *Fetch   `yaml:"fetch,omitempty" json:"fetch,omitempty"`
	Fixes    []string `yaml:"fixes,omitempty" json:"fixes,omitempty"`

	// Bundle.
	Application string          `yaml:"application,omitempty" json:"application,omitempty"`
	Profiles    []BundleProfile `yaml:"profiles,omitempty" json:"profiles,omitempty"`

	// Path is the file's path relative to the catalog directory, with
	// forward slashes. It is not part of the frontmatter; the loader sets it.
	Path string `yaml:"-" json:"path"`
}

// Fetch says where the module of a variant is downloaded from.
type Fetch struct {
	URLs   []string `yaml:"urls" json:"urls"`
	SHA256 string   `yaml:"sha256" json:"sha256"`
	Format string   `yaml:"format" json:"format"`
	Member string   `yaml:"member,omitempty" json:"member,omitempty"`
}

// BundleProfile limits automatic installation to a measured combination.
type BundleProfile struct {
	Version    string `yaml:"version" json:"version"`
	ExeSHA256  string `yaml:"exe_sha256" json:"exe_sha256"`
	Wine       string `yaml:"wine" json:"wine"`
	HostArch   string `yaml:"host_arch" json:"host_arch"`
	PrefixArch string `yaml:"prefix_arch" json:"prefix_arch"`
	// Release is the GitHub release tag with prebuilt modules for this
	// profile. Bump it whenever the bundle's fixes or patches change.
	Release string `yaml:"release,omitempty" json:"release,omitempty"`
}
