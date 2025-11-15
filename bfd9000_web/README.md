# FILE: /bfd9000_web/README.md

# BFD9000 Django Application

This project is a Django web application named BFD9000. It is structured to run using Nix flakes for dependency management and environment setup.

## Prerequisites

- Ensure you have Nix installed on your system. You can find installation instructions at [Nix Installation](https://nixos.org/download.html).

## Setting Up the Environment

1. Navigate to the project directory:

   ```bash
   cd /path/to/bfd9000_web
   ```

2. Build the Nix environment:

   ```bash
   nix build .#devShell
   ```

3. Enter the Nix shell:

   ```bash
   nix develop
   ```

## Running the Django Application

1. Make sure to apply any database migrations:

   ```bash
   python manage.py migrate
   ```

2. Start the Django development server:

   ```bash
   python manage.py runserver
   ```

3. Open your web browser and go to `http://127.0.0.1:8000` to view the application.

## Additional Information

- The application settings can be found in `bfd9000/settings.py`.
- URL routing is defined in `bfd9000/urls.py`.
- For deployment, refer to the WSGI configuration in `bfd9000/wsgi.py`.

Feel free to explore the code and contribute to the project!