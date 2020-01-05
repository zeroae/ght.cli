const { inspect } = require("util");
const core = require("@actions/core");
const exec = require("@actions/exec");
const setupPython = require("./src/setup-python");

async function run() {
  try {
    // Allows ncc to find assets to be included in the distribution
    const src = __dirname + "/src";
    core.debug(`src: ${src}`);

    // Setup Python from the tool cache
    setupPython("3.8.0", "x64");

    // Install requirements
    await exec.exec("pip", [
      "install",
      "--requirement",
      `${src}/requirements.txt`
    ]);

    // Fetch action inputs
    const inputs = {
      template: core.getInput("template"),
    };
    core.debug(`Inputs: ${inspect(inputs)}`);

    // Execute python script
    await exec.exec("python", [
      `${src}/action.py`,
        // TODO: How to get https://github.com/ from environment, for github enterprise
      `https://github.com/${inputs.template}`,
    ]);
  } catch (error) {
    core.setFailed(error.message);
  }
}

run();
