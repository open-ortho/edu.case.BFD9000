{
  description = "Django development environment using Nix flakes";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05"; # or unstable
  };

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-darwin"
      ];
      forEachSystem = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forEachSystem (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
          python = pkgs.python311;
        in
        {
          default = pkgs.mkShell {
            name = "django-env";

            buildInputs = [
              python
              python.pkgs.pip
              pkgs.watchman
            ];

            # Why this shellHook exists:
            # - Python dependencies are defined in requirements files, not flake.nix.
            # - direnv users get setup via .envrc, but plain `nix develop` users need the
            #   same automatic bootstrap behavior.
            #
            # If you do not use direnv:
            # 1) run `nix develop` from the repository root
            # 2) the hook below creates/activates `.venv` and syncs dependencies
            # 3) run Python/Django commands normally (`python ...`, `pytest ...`)
            shellHook = ''
                            if [ ! -d .venv ]; then
                              python -m venv .venv
                            fi
                            . .venv/bin/activate

                            req_file="bfd9000_web/requirements-dev.txt"
                            stamp_file=".venv/.bfd9000_requirements_stamp"
                            req_hash="$(python - "$req_file" <<'PY'
              import hashlib
              import pathlib
              import sys

              path = pathlib.Path(sys.argv[1])
              print(hashlib.sha256(path.read_bytes()).hexdigest())
              PY
                            )"

                            stamp_hash=""
                            if [ -f "$stamp_file" ]; then
                              IFS= read -r stamp_hash < "$stamp_file"
                            fi

                            if [ "$req_hash" != "$stamp_hash" ]; then
                              python -m pip install -r "$req_file"
                              echo "$req_hash" > "$stamp_file"
                              deps_status="[installed]"
                            else
                              deps_status="[up to date]"
                            fi

                            echo "[nix] .venv Python: $(python --version) deps: $deps_status"
                            unset req_file stamp_file req_hash stamp_hash deps_status
            '';

          };
        }
      );
    };
}
