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
              python.pkgs.django
              python.pkgs.djangorestframework
              python.pkgs.django-cors-headers
              python.pkgs.django-filter
              python.pkgs.drf-spectacular
              python.pkgs.drf-nested-routers
              python.pkgs.pillow
              python.pkgs.openpyxl
              python.pkgs.whitenoise
              python.pkgs.pip
              pkgs.watchman
            ];

            # Optional: environment variables for Django
            # export DJANGO_SETTINGS_MODULE if needed
            shellHook = ''
              echo "Django development environment activated."
              echo "Python: $(python --version)"
            '';
          };
        }
      );
    };
}
