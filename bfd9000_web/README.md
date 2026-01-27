# BFD9000 Django Application

## Prerequisites

There is a nix flake for setting up a developer shell though this is optional.
To use it, install [Nix](https://nixos.org/download.html) and run the following command from the workspace root:

```bash
nix develop
```

Alternatively just install django with python.

## Running the Django Application

1. Make sure to apply any database migrations:

   ```bash
   cd bfd9000_web
   python manage.py migrate
   ```

2. Start the Django development server:

   ```bash
   python manage.py runserver
   ```

3. Open your web browser and go to `http://127.0.0.1:8000` to view the application.

## Running Tests

```bash
cd bfd9000_web
python manage.py test
```

Run specific test modules:

```bash
python manage.py test archive.tests.test_api_flows
python manage.py test archive.tests.test_valuesets
```

Useful test options:
- `--failfast` - Stop after first failure
- `-v 2` - Verbose output
- `--keepdb` - Keep test database between runs (faster)
- `--parallel` - Run tests in parallel

**Note**: Tests automatically clean up uploaded media files. Test images are stored in a temporary directory that is deleted after tests complete, so they won't clutter your `media/uploads/` directory.

## Additional Information

- The application settings can be found in `bfd9000/settings.py`.
- URL routing is defined in `bfd9000/urls.py`.
- For deployment, refer to the WSGI configuration in `bfd9000/wsgi.py`.

