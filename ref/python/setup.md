
# Environment Setup Instructions

This README provides detailed instructions on how to set up your Python environment using Miniconda and Mamba for improved package management and faster resolution.

## Step 1: Install Miniconda

Miniconda is a minimal installer for Conda. It is smaller than the full Anaconda distribution and includes only Conda, its dependencies, and Python.

### Windows, Mac, and Linux Instructions:

1. Download the Miniconda installer:
   - **Windows**: [Miniconda Windows Installer](https://docs.conda.io/en/latest/miniconda.html#windows-installers)
   - **Mac**: [Miniconda MacOS Installer](https://docs.conda.io/en/latest/miniconda.html#macos-installers)
   - **Linux**: [Miniconda Linux Installer](https://docs.conda.io/en/latest/miniconda.html#linux-installers)

2. Follow the installation instructions for your operating system on the [Miniconda installation page](https://conda.io/projects/conda/en/latest/user-guide/install/index.html).

## Step 2: Set up Mamba

Mamba is a fast, robust, and cross-platform package manager built on top of Conda, designed to be drop-in compatible with Conda but with faster and more reliable solutions for package installations and environment management.

1. Open your terminal or command prompt.
2. Update Conda:
   ```
   conda update conda
   ```
3. Install Mamba in the base environment:
   ```
   conda install mamba -n base -c conda-forge
   ```

## Step 3: Create and Activate the Environment

1. Save the provided `environment.yml` file to your local machine.
2. Using your terminal or command prompt, navigate to the directory containing the `environment.yml` file.
3. Create the environment using Mamba:
   ```
   mamba env create -f environment.yml
   ```
4. Activate the new environment:
   ```
   conda activate ci2d3env
   ```

## Step 4: Verify the Installation

Check that all required packages are installed correctly:
```
conda list
```

You are now ready to start working on the project with all the necessary Python packages installed!

## Troubleshooting

If you encounter any issues during the installation or environment setup, refer to the [Conda documentation](https://docs.conda.io/projects/conda/en/latest/user-guide/troubleshooting.html) for troubleshooting tips.
