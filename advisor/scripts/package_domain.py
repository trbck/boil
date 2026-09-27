#!/usr/bin/env python3
"""Export one domain as a self-contained `.skill` bundle.

Git is the primary distribution channel (it ships inside boil, see `boil advise`). This exists for
runtimes that cannot clone — a cloud sandbox, a shared skill registry, a colleague
who should get the decisions corpus and nothing else.

Two things make the bundle correct rather than merely smaller:

  1. **Engine packs are excluded by default.** They are licensed vendor
     documentation, they are gitignored for that reason, and they are the bulk of
     the bytes (22 MB vs 1.4 MB). `--include-engines` overrides, and warns.

  2. **The bundle is rebuilt, not copied.** SKILL.md's description, the retrieval
     examples, the engine instructions and the domain table are all generated from
     *installed* domains. Copying this repo's SKILL.md into a single-domain bundle
     would ship a description advertising domains the bundle does not contain, and
     `--engine` examples for documentation it does not carry. So the staging tree
     is assembled first and the real `build_index.py` runs inside it, where ROOT
     resolves to the staging directory and the generated surface describes exactly
     what shipped.

Usage:
    python3 scripts/package_domain.py --domain decisions
    python3 scripts/package_domain.py --domain trading --include-engines
    python3 scripts/package_domain.py --all --out dist/
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ka_common as K  # noqa: E402

# Everything a bundle needs to answer a question and rebuild itself. Anything not
# listed is deliberately absent: tests/ pins IDs for this repo's refactors, and
# .git is the whole point of not using git.
TOPLEVEL_FILES = ["FORMAT.md", "README.md"]
TOPLEVEL_DIRS = ["scripts", "templates", "references", "bin"]

SKIP_DIR_NAMES = {"__pycache__", ".git", ".DS_Store"}
SKIP_SUFFIXES = (".pyc", ".suggested.json")
SKIP_NAMES = {"registry.candidates.md", ".DS_Store"}

# Fixed timestamp so the same corpus produces a byte-identical bundle. Zip stores
# mtimes, and a bundle whose checksum changes on every build cannot be diffed.
ZIP_DATE = (1980, 1, 1, 0, 0, 0)


def human(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return "%.1f %s" % (size, unit) if unit != "B" else "%d B" % size
        size /= 1024.0


def skip(name):
    return (name in SKIP_NAMES or name in SKIP_DIR_NAMES
            or name.endswith(SKIP_SUFFIXES))


def copy_tree(src, dst):
    """Copy a directory, dropping build litter and review files."""
    if not os.path.isdir(src):
        return
    for root, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if not skip(d))
        rel = os.path.relpath(root, src)
        target = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target, exist_ok=True)
        for name in sorted(files):
            if skip(name):
                continue
            shutil.copy2(os.path.join(root, name), os.path.join(target, name))


def stage(domain, staging, include_engines):
    """Assemble a single-domain tree; return the packs that were dropped."""
    for name in TOPLEVEL_FILES:
        path = os.path.join(K.ROOT, name)
        if os.path.exists(path):
            shutil.copy2(path, os.path.join(staging, name))
    for name in TOPLEVEL_DIRS:
        copy_tree(os.path.join(K.ROOT, name), os.path.join(staging, name))

    # inbox/ ships as an empty drop zone with its contract, never with its contents.
    os.makedirs(os.path.join(staging, "inbox"), exist_ok=True)
    readme = os.path.join(K.ROOT, "inbox", "README.md")
    if os.path.exists(readme):
        shutil.copy2(readme, os.path.join(staging, "inbox", "README.md"))

    dom_src = os.path.join(K.DOMAINS_DIR, domain["id"])
    dom_dst = os.path.join(staging, "domains", domain["id"])
    copy_tree(dom_src, dom_dst)

    packs = K.load_domain_packs(domain)
    dropped = []
    if not include_engines:
        kept = []
        for pack in packs:
            if pack.get("kind") == "engine":
                dropped.append(pack)
                shutil.rmtree(os.path.join(dom_dst, pack["path"]), ignore_errors=True)
            else:
                kept.append(pack)
        if dropped:
            # Rewrite the staged registry so the build never looks for what was cut.
            manifest_name = domain.get("packs", "packs.json")
            manifest = os.path.join(dom_dst, os.path.basename(manifest_name))
            data = K.load_json(manifest)
            data["packs"] = [{k: v for k, v in p.items()
                              if k not in ("abs_path", "domain")} for p in kept]
            with open(manifest, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
    return dropped


RULE_REF_RE = re.compile(r"\b([A-Z][A-Z0-9]*-\d+-R\d+)\b")


def external_citations(staging, domain_id):
    """Rule IDs cited in the bundled conflicts.md that the bundle cannot resolve.

    The registry deliberately records cross-domain convergences, so these are not
    errors — but a reader inside the bundle has no way to verify them, and the
    skill's first rule is never to cite an ID you have not read. Report them so the
    exporter knows what the recipient will not be able to check.
    """
    conflicts = os.path.join(staging, "domains", domain_id, "conflicts.md")
    if not os.path.exists(conflicts):
        return []
    index = K.load_json(os.path.join(staging, "generated", domain_id, "index.json"))
    known = {r["id"] for r in index.get("rules", [])}
    seen, out = set(), []
    with open(conflicts, encoding="utf-8") as fh:
        for line in fh:
            for ref in RULE_REF_RE.findall(line):
                if ref not in known and ref not in seen:
                    seen.add(ref)
                    out.append(ref)
    return out


def run(staging, script, *args):
    proc = subprocess.run([sys.executable, os.path.join("scripts", script)] + list(args),
                          cwd=staging, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def write_zip(staging, out_path):
    entries = []
    for root, dirs, files in os.walk(staging):
        dirs[:] = sorted(d for d in dirs if not skip(d))
        for name in sorted(files):
            if skip(name):
                continue
            full = os.path.join(root, name)
            entries.append((os.path.relpath(full, staging), full))
    entries.sort()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, full in entries:
            info = zipfile.ZipInfo(arcname, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (os.stat(full).st_mode & 0xFFFF) << 16
            with open(full, "rb") as fh:
                zf.writestr(info, fh.read())
    return len(entries)


def package(domain, out_dir, include_engines, keep_staging=False):
    staging = tempfile.mkdtemp(prefix="advisor-pkg-")
    try:
        dropped = stage(domain, staging, include_engines)

        code, out = run(staging, "build_index.py", "--quiet")
        if code != 0:
            print(out)
            return "build failed for %s" % domain["id"]

        code, out = run(staging, "validate_pack.py")
        if code != 0:
            print(out)
            return "validation failed for %s" % domain["id"]

        index = K.load_json(os.path.join(staging, "generated", domain["id"], "index.json"))
        out_path = os.path.join(out_dir, "advisor-%s.skill" % domain["id"])
        count = write_zip(staging, out_path)
        size = os.path.getsize(out_path)

        print("%-11s %-28s %8s  %3d files · %d rules · %d chapters"
              % (domain["id"], os.path.basename(out_path), human(size), count,
                 len(index.get("rules", [])), len(index.get("chapters", []))))
        external = external_citations(staging, domain["id"])
        if external:
            shown = ", ".join(external[:6])
            more = " (+%d more)" % (len(external) - 6) if len(external) > 6 else ""
            print("            %d cross-domain citation(s) unresolvable in this bundle: %s%s"
                  % (len(external), shown, more))
        for pack in dropped:
            print("            excluded engine pack `%s` (%s) — licensed vendor docs"
                  % (pack["id"], pack.get("title", "")))
        if include_engines and any(p.get("kind") == "engine" for p in K.load_domain_packs(domain)):
            print("            ! engine packs INCLUDED — check the licence before sharing this "
                  "bundle")
        if keep_staging:
            print("            staging kept at %s" % staging)
            staging = None
        return None
    finally:
        if staging:
            shutil.rmtree(staging, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--domain", help="domain id to package")
    ap.add_argument("--all", action="store_true", help="package every installed domain")
    ap.add_argument("--out", default="dist", help="output directory (default: dist/)")
    ap.add_argument("--include-engines", action="store_true",
                    help="ship engine packs too — large, and licensed; check before sharing")
    ap.add_argument("--keep-staging", action="store_true",
                    help="leave the staging tree on disk for inspection")
    args = ap.parse_args()

    if not args.domain and not args.all:
        ap.error("pass --domain <id> or --all")

    domains = K.load_domains(None if args.all else args.domain)
    if not domains:
        sys.exit("no domain matching %r — try: python3 scripts/lookup.py --list domains"
                 % args.domain)

    out_dir = args.out if os.path.isabs(args.out) else os.path.join(K.ROOT, args.out)
    failures = []
    for domain in domains:
        err = package(domain, out_dir, args.include_engines, args.keep_staging)
        if err:
            failures.append(err)

    if failures:
        for err in failures:
            print("! %s" % err)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
