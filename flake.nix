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

          # Custom build for boxsdk
          boxsdk = python.pkgs.buildPythonPackage rec {
            pname = "boxsdk";
            version = "10.4.0";
            format = "setuptools";

            src = pkgs.fetchPypi {
              inherit pname version;
              sha256 = "sha256-SivU2qxxpkAD8dvuRVDFvIFvNMuBIT6JqT3HF7e1HKQ=";
            };

            propagatedBuildInputs = with python.pkgs; [
              requests
              requests_toolbelt
              pyjwt
              cryptography
            ];

            doCheck = false;

            meta = with pkgs.lib; {
              description = "Official Box Python SDK";
              homepage = "https://github.com/box/box-python-sdk";
              license = licenses.asl20;
            };
          };
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
              python.pkgs.pylint
              python.pkgs.django-stubs
              python.pkgs.djangorestframework-stubs
              python.pkgs.pip
              python.pkgs.python-dotenv
              boxsdk
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
