# Github Template Renderer
[![Actions Status](https://github.com/peter-evans/python-action/workflows/Python%20Action/badge.svg)](https://github.com/peter-evans/python-action/actions)

A GitHub Action for rendering GitHub Templates written with the Jinja2 templating language.

## Usage

### Develop action

- Modify [`action.yml`](action.yml) to describe the action
- Modify [`index.js`](index.js) to pass action inputs to the Python script
- Set the version of Python required in [`index.js`](index.js)
    ```javascript
        // Setup Python from the tool cache
        setupPython("3.8.0", "x64");
    ```
- Add Python dependencies to [`requirements.txt`](src/requirements.txt)
- Add Python dependencies to [`environment.yml`](environment.yml)

### Install dependencies

```
conda env create
conda activate ght-render-dev
npm install
```

### Package for distribution

```
npm run build
```

**Note**: Packaging the action is necessary even when making changes to the Python source code in `src`. Changes made will be packaged into `dist`.

### Release

1. Commit the `dist` directory changes to `master`
2. Tag the commit or make a GitHub release

## License

[MIT](LICENSE)
