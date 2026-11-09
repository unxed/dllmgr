# #51 plain launch stays on the system Wine

owner-far2l-trace.log (owner, 2026-11-09 15:58, far2l, `wine Photoshop.exe`, fixme/font/AlphaBlend/ReleaseDC filtered out): the trampoline starts the launcher, then nothing at all from it (no Python error, no private-runtime trace line although DLLMGR27_DEBUG is inherited), fallback after 15 s. The stand hands over in under 1.5 s (plain, setsid, pty). Next: launch log (c97e359) + `ps` on the owner machine.
