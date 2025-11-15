# BFD9000 Django Application

## Prerequisites

There is a nix flake for setting up a developer shell though this is optional.
To use it, install [Nix](https://nixos.org/download.html) and run the following command from the workspace root:

```bash
nix develop
```

Alternatively just install django with python.

## Running the Django Application

From the workspace root:

1. Make sure to apply any database migrations:

   ```bash
   python bfd9000_web/manage.py migrate
   ```

2. Start the Django development server:

   ```bash
   python bfd9000_web/manage.py runserver
   ```

3. Open your web browser and go to `http://127.0.0.1:8000` to view the application.

## Additional Information

- The application settings can be found in `bfd9000/settings.py`.
- URL routing is defined in `bfd9000/urls.py`.
- For deployment, refer to the WSGI configuration in `bfd9000/wsgi.py`.

