# Publish this replication package under Malihe Aliasgari's GitHub account

The initial replication data and analysis code in this GitHub-ready directory come from `SNFF_replication_package_v4.0.zip`. The underlying datasets, scripts and results are unchanged; README and SHA-256 manifest are adjusted for a public repository, and author/setup documentation and a checksum workflow are added. Preserve the original ZIP unchanged for an archival deposit if you need its original archive hash.

## GitHub website workflow

1. **Malihe signs in to her own GitHub account**, opens **New repository**, chooses the owner corresponding to her account, repository name **FDIC-SNFF-Decision-Framework**, and chooses **Public** once all authors have approved publication. Do not generate a starter README or license on the GitHub form; this package already contains a README and licensing still needs an agreed choice.
2. Extract `SNFF_Malihe_GitHub_Ready_v4.0.zip` locally. Upload the **files and folders inside the extracted ZIP** to the empty repository, preserving their folders. The browser UI normally accepts up to 100 files at a time; if it does not preserve nested directories, use GitHub Desktop or Git from the extracted directory. Commit as Malihe. Do **not** upload just the ZIP as the only repository content.
3. In **Settings → Collaborators / Access → Add people**, Malihe invites **`Nejatbakhsh-y`**. Yousef accepts the invitation through GitHub. This grants collaborator access but does not automatically credit past commits to him.
4. To show **Yousef as a code contributor**, Yousef should contribute and commit legitimate documentation, tests, or fixes using an email verified on his GitHub account, or use GitHub-supported `Co-authored-by` commit trailers for actual joint commits. Do not create fictitious contributions.
5. Review third-party redistribution rules and **choose licenses with all authors' approval**. Document the code license and the permissions for data or derived materials. No license has been imposed by this prepared package.
6. In GitHub, publish a **Release** with tag `v4.0`, identifying the exact version for the manuscript. Check that a new clone passes `sha256sum -c MANIFEST.sha256`, and run `bash reproduce.sh` in the pinned environment if possible.
7. Archive the approved release in **Zenodo** or an equivalent service, obtain its DOI and add both the repository URL and DOI to the manuscript's **Data and Code Availability** statement. If you deposit the original `SNFF_replication_package_v4.0.zip` unchanged, its SHA-256 is `a2479df40433665a4cba58daf5019ec1503359b555d272ab149fa6b0a3d69425`. Note that the GitHub-ready ZIP is not byte-identical to the original archive; the research files themselves are preserved.

## Co-authorship versus GitHub collaboration

* The scientific paper already lists Yousef Nejatbakhsh as a coauthor (first author) and Malihe Aliasgari as corresponding author.
* `CITATION.cff` and `AUTHORS.md` make this authorship explicit in the repository.
* An invitation via GitHub Settings adds **collaborator access**; only Git commits attributed to Yousef's account establish his code-contributor history.
* A GitHub `Co-authored-by` trailer uses the exact form `Co-authored-by: Yousef Nejatbakhsh <EMAIL_VERIFIED_ON_GITHUB>`, only for genuine jointly authored commits.

## Verification

```bash
sha256sum -c MANIFEST.sha256
pip install -r requirements.txt
bash reproduce.sh
```

The analysis reproduction is resource-intensive; some upstream price-dependent steps cannot run because raw price series are intentionally excluded. See README for limitations.
