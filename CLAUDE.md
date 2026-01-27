Currently, the primary development focus is on the Django server in `bfd9000_web`. If dependencies are missing, this project does use a nix flake at its root, so try running `nix develop` to set up the development environment properly.

The github action uses the nix flake as well. Any time you add another dependency or python package, make sure to update the flake.nix file.

## Reference

- **Main API spec**: [api_requirements.md](./bfd9000_web/docs/api_requirements.md)

Whenever a large change is made, documenting it in `./bfd9000_web/docs` is good practice.
