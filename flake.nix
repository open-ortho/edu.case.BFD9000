{
  description = "Django development environment using Nix flakes";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";  # or unstable
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      python = pkgs.python311; # pick your Python version
    in {

      devShells.${system}.default = pkgs.mkShell {
        name = "django-env";

        buildInputs = [
          python
          python.pkgs.django
          python.pkgs.pip
        ];

        # Optional: environment variables for Django
        # export DJANGO_SETTINGS_MODULE if needed
        shellHook = ''
          echo "Django development environment activated."
          echo "Python: $(python --version)"
        '';
      };
    };
}