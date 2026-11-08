Apply `fix-it-in-wine-shared-scope.patch` to fix-it-in-wine main
f5334a13e61da0f2c2a7ccf215f0da76b4295e56. This is supplied for the owner to
apply, rather than pushed to another repository. It guards new shared-slot
apply, keeps undo available, and corrects the skill's isolation guarantee.
Shared-slot unit fixtures explicitly opt into `--allow-shared-prefix` when
testing that legacy scope; an additional test proves the default refuses
before files, backups or registry are changed.
The appdir API by itself is not a general isolation solution, either.
