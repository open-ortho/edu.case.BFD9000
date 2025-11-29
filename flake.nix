{
  description = "Django development environment using Nix flakes";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";  # or unstable
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in {

      devShells.${system}.default = pkgs.mkShell {
        name = "django-env";

        buildInputs = with pkgs; [
          python311
          python311.pkgs.django
          python311.pkgs.pip
          watchman
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