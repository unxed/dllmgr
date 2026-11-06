// Command dllmgr-catalog validates the catalog and compiles its index.
//
//	dllmgr-catalog check <dir>   validate every entry under <dir>
//	dllmgr-catalog build <dir>   check, then write <dir>/index.json
package main

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/unxed/dllmgr/internal/catalog"
)

func main() {
	os.Exit(run(os.Args[1:]))
}

func run(args []string) int {
	if len(args) != 2 || (args[0] != "check" && args[0] != "build") {
		fmt.Fprintln(os.Stderr, "usage: dllmgr-catalog check <dir> | build <dir>")
		return 2
	}
	cmd, dir := args[0], args[1]
	entries, err := catalog.LoadDir(dir)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	if cmd == "check" {
		fmt.Printf("%s: %d entries ok\n", dir, len(entries))
		return 0
	}
	data, err := catalog.BuildIndex(entries)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	out := filepath.Join(dir, "index.json")
	if err := os.WriteFile(out, data, 0o644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	fmt.Printf("%s: %d entries\n", out, len(entries))
	return 0
}
