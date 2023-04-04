# TreeGen4Gpt (v0.0.1-alpha)

TreeGen4Gpt is a handy tool designed to generate templates for programming projects, making it easier to transfer the project structure and content to GPT-4 or other AI models and streamlining the process. Initially created for Python projects, TreeGen4Gpt aims to support various programming languages in the future, making it a useful addition to any developer's toolkit.

## Features

- Generate a project template with a hierarchy of project's files and folders
- Ignore specific folders or files based on names or patterns
- Include or exclude Python files as needed
- Options to remove comments, docstrings, or specific functions/methods from the included files
- Save and reload the project state for future use
- Command-line interface and a graphical user interface (GUI) built with Tkinter for ease of use

## Usage

TreeGen4Gpt can be used with or without the GUI. To run the script without the GUI, use the `--cli` command-line argument. You can also specify the working directory using the `--dir` argument.

```bash
python main.py --cli --dir /path/to/your/project
```

To run the script with the GUI, simply execute the script without any arguments:

```bash
python main.py
```

## Installation

1. Clone the repository:

```bash
git clone https://github.com/E-B3rry/treegen4gpt.git
```

2. Change the working directory:

```bash
cd treegen4gpt
```

3. Run the script:

```bash
python treegen4gpt.py
```

## Documentation

A comprehensive guide on how to use TreeGen4Gpt will be provided soon. Once available, the documentation will cover:

- Installation and setup
- Using the command-line interface
- Using the graphical user interface (GUI)
- Customizing the template generation process
- Troubleshooting common issues

In the meantime, you can explore the script's functionality by running it and experimenting with the command-line interface and the graphical user interface (GUI). If you have any questions or need assistance, feel free to reach out.

## Contributing

Although this is a personal project, contributions are welcome! If you'd like to contribute to TreeGen4Gpt, please follow these steps:

1. Fork the repository on GitHub
2. Create a new branch for your feature or bugfix
3. Make your changes and commit them with descriptive commit messages
4. Push your changes to your fork on GitHub
5. Create a pull request against the main repository

Please ensure that your code adheres to the project's style guidelines and is well-documented. Writing tests for your changes is also encouraged to ensure correctness and prevent regressions.

## Support

If you encounter any issues or have questions about TreeGen4Gpt, please open an issue on GitHub or feel free to reach out. Assistance is always available!

## License

TreeGen4Gpt is released under the [Apache License 2.0](LICENSE). By using, modifying, or distributing this project, you agree to the terms and conditions of this license.