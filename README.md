# ObjoPublisher

**ObjoPublisher** is a collection of reusable GitHub Actions workflows for publishing applications created with **Objo Studio**.

The repository centralizes all publishing logic so that individual application repositories only need small wrapper workflows that provide project-specific parameters and secrets.

Using reusable workflows has several advantages:

- Publishing logic is maintained in one place.
- Improvements automatically benefit every project.
- Build workflows remain small and easy to understand.
- Publishing behavior is consistent across all projects.
- Objo Studio installation and caching are handled automatically.
- License activation and cleanup are handled automatically.

---

# Available reusable workflows

| Workflow | Description |
|----------|-------------|
| **publish_objo_macos.yml** | Publishes macOS applications, optionally signs and notarizes them using Apple Developer certificates. |
| **publish_objo_linux.yml** | Publishes Linux applications for one or more runtime targets. |
| **publish_objo_windows.yml** | Publishes Windows applications and signs generated MSIX packages using the official Azure Trusted Signing GitHub Action. |
| **publish_objo_windows_objosign.yml** | Publishes Windows applications and lets Objo Studio perform Azure Trusted Signing during publishing. |

---

# General features

All reusable workflows share the same design principles.

## Automatic Objo Studio installation

If the requested version of Objo Studio is already cached on the GitHub runner, it is restored immediately.

Otherwise the workflow automatically downloads the requested version from the official Objo download site and stores it in the GitHub Actions cache for future workflow runs.

By default the latest released version of Objo Studio is used.

---

## Automatic license management

Whenever publishing requires an activated Objo Studio license, the workflow automatically

1. creates a temporary license file,
2. activates the license,
3. performs the requested publish operation,
4. deactivates the license,
5. removes the temporary license file.

License deactivation is performed even when publishing fails.

---

## Output directories

Instead of publishing into fixed platform-specific folders, every workflow publishes into a directory under the current runner user's home directory.

Default locations are:

| Platform | Default output directory |
|----------|--------------------------|
| macOS | `$HOME/Documents/Publish` |
| Linux | `$HOME/Publish` |
| Windows | `%USERPROFILE%\Publish` |

The output directory can be changed using the `output-directory` workflow input.

---

## Multiple publish targets

The macOS, Linux and Windows reusable workflows support publishing multiple runtime identifiers in a single execution.

Example:

```yaml
with:
  targets: "osx-arm64, osx-x64"
```

```yaml
with:
  targets: "linux-x64, linux-arm64"
```

```yaml
with:
  targets: "win-x64, win-arm64"
```

Whitespace around target names is ignored automatically.

---

## Selecting the Objo Studio version

By default every reusable workflow automatically determines the latest released version of Objo Studio.

A specific version can be requested:

```yaml
with:
  objo-version: "26.7.1"
```

---

## Repository structure

```
.github/
└── workflows/
    publish_objo_linux.yml
    publish_objo_macos.yml
    publish_objo_windows.yml
    publish_objo_windows_objosign.yml
```

Each workflow can be called from another repository using:

```yaml
jobs:
  publish:
    uses: madamov/ObjoPublisher/.github/workflows/<workflow>.yml@v1
```

---

# Workflow documentation

The following sections describe each reusable workflow in detail.

# publish_objo_macos.yml

Publishes one or more macOS application bundles created with Objo Studio.

Depending on the available secrets, the workflow can produce either:

- unsigned DMG packages, or
- fully signed and notarized DMG packages ready for distribution.

Apple code signing is **optional**. If the Apple signing secrets are not supplied, the workflow automatically skips all signing and notarization steps and produces unsigned DMG files.

---

## Publishing process

```text
Checkout repository
        │
        ▼
Validate inputs
        │
        ▼
Determine Objo Studio version
        │
        ▼
Restore or download Objo Studio
        │
        ▼
(Optional)
Install Apple signing certificate
        │
        ▼
(Optional)
Create notarization profile
        │
        ▼
(Optional)
Update project.json
        │
        ▼
Activate Objo Studio license
        │
        ▼
Publish application
        │
        ▼
Collect DMG files
        │
        ▼
Upload artifacts
        │
        ▼
Deactivate license
```

---

## Workflow inputs

| Input | Required | Default | Description |
|--------|:-------:|---------|-------------|
| `solution-file` | ✔ | | Path to the Objo solution file. |
| `project-file` | ✔ | | Path to `project.json`. |
| `application-name` | ✔ | | Application name used when collecting artifacts. |
| `output-directory` | | `Publish` | Output directory under `$HOME/Documents`. |
| `targets` | | `osx-arm64,osx-x64` | Comma-separated list of runtime identifiers. |
| `artifact-name` | | `objo-macos-publish` | Uploaded artifact name. |
| `apple-notary-profile` | | `objo-notarization` | Name of the temporary notarytool profile. |
| `objo-version` | | latest | Specific Objo Studio version to use. |

---

## Workflow secrets

### Required

| Secret | Description |
|---------|-------------|
| `objo-license` | Objo Studio license key. |

### Optional

If every Apple signing secret below is supplied, the application is signed and notarized.

If one or more are omitted, publishing continues without signing.

| Secret | Description |
|---------|-------------|
| `apple-certificate` | Base64 encoded Apple Developer certificate (.p12). |
| `apple-certificate-name` | Signing identity name. |
| `apple-certificate-password` | Password protecting the .p12 file. |
| `apple-team-id` | Apple Developer Team ID. |
| `apple-id` | Apple Developer account email address. |
| `apple-app-specific-password` | App-specific password used by `notarytool`. |

---

## Runtime identifiers

Supported runtime identifiers are those supported by Objo Studio.

Typical examples are:

| Runtime identifier | Platform |
|--------------------|----------|
| `osx-arm64` | Apple Silicon |
| `osx-x64` | Intel Macs |

Example:

```yaml
with:
  targets: "osx-arm64"
```

or

```yaml
with:
  targets: "osx-arm64, osx-x64"
```

---

## Output directory

The default output directory is

```text
$HOME/Documents/Publish
```

It can be overridden:

```yaml
with:
  output-directory: Documents/MyApplication
```

which becomes

```text
$HOME/Documents/MyApplication
```

Absolute paths are also supported.

---

## Generated artifacts

The workflow automatically collects every generated DMG.

Typical uploaded artifacts are:

```
MyApplication-macOS-Apple-Silicon.dmg
MyApplication-macOS-Intel.dmg
```

Only artifacts that actually exist are uploaded.

For example, when publishing only

```yaml
targets: osx-arm64
```

only the Apple Silicon DMG is uploaded.

---

## Example

```yaml
jobs:
  publish:
    uses: madamov/ObjoPublisher/.github/workflows/publish_objo_macos.yml@v1

    with:
      solution-file: MyGreatApp.objosln
      project-file: Projects/MyGreatApp/project.json
      application-name: MyGreatApp

      output-directory: Publish

      targets: "osx-arm64, osx-x64"

      artifact-name: mygreatapp-macos

      # Optional
      # objo-version: "26.7.1"

    secrets:
      objo-license: ${{ secrets.OBJO_LICENSE }}

      apple-certificate: ${{ secrets.APPLE_CERTIFICATE }}
      apple-certificate-name: ${{ secrets.APPLE_CERTIFICATE_NAME }}
      apple-certificate-password: ${{ secrets.APPLE_CERTIFICATE_PASSWORD }}

      apple-team-id: ${{ secrets.APPLE_TEAM_ID }}
      apple-id: ${{ secrets.APPLE_ID }}
      apple-app-specific-password: ${{ secrets.APPLE_APP_SPECIFIC_PASSWORD }}
```

---

## Notes

- The workflow automatically creates and removes a temporary keychain.
- The temporary notarization profile exists only for the duration of the workflow.
- The Objo Studio license is always deactivated before the workflow finishes.
- The downloaded Objo Studio installation is cached by version.
- If Apple signing is disabled, the workflow still produces valid unsigned DMG files.

---

# publish_objo_linux.yml

Publishes one or more Linux applications created with Objo Studio.

The workflow restores or downloads the requested Objo Studio version, activates an Objo Studio license, publishes the application for one or more Linux runtime identifiers, collects the generated archives, uploads them as workflow artifacts, and finally deactivates the license.

Unlike the macOS and Windows workflows, Linux publishing does not require any platform-specific signing.

---

## Publishing process

```text
Checkout repository
        │
        ▼
Validate inputs
        │
        ▼
Determine Objo Studio version
        │
        ▼
Restore or download Objo Studio
        │
        ▼
Activate Objo Studio license
        │
        ▼
Publish application
        │
        ▼
Collect Linux archives
        │
        ▼
Upload artifacts
        │
        ▼
Deactivate license
```

---

## Workflow inputs

| Input | Required | Default | Description |
|--------|:-------:|---------|-------------|
| `solution-file` | ✔ | | Path to the Objo solution file. |
| `project-file` | ✔ | | Path to `project.json`. |
| `application-name` | ✔ | | Application name used when naming uploaded artifacts. |
| `output-directory` | | `Publish` | Output directory under the current user's home directory. |
| `targets` | | `linux-x64` | Comma-separated list of Linux runtime identifiers. |
| `artifact-name` | | `objo-linux-publish` | Uploaded artifact name. |
| `objo-version` | | latest | Specific Objo Studio version to use. |

---

## Workflow secrets

| Secret | Required | Description |
|---------|:-------:|-------------|
| `objo-license` | ✔ | Objo Studio license key used during publishing. |

No additional secrets are required.

---

## Runtime identifiers

The workflow supports any Linux runtime identifier supported by Objo Studio.

Typical examples include:

| Runtime identifier | Platform |
|--------------------|----------|
| `linux-x64` | 64-bit Intel/AMD Linux |
| `linux-arm64` | ARM64 Linux |

Examples:

```yaml
with:
  targets: "linux-x64"
```

or

```yaml
with:
  targets: "linux-x64, linux-arm64"
```

Whitespace surrounding runtime identifiers is ignored automatically.

---

## Output directory

The default output directory is

```text
$HOME/Publish
```

It can be overridden:

```yaml
with:
  output-directory: Applications/MyGreatApp
```

which becomes

```text
$HOME/Applications/MyGreatApp
```

Absolute paths are also supported.

---

## Generated artifacts

The workflow searches the publish directory recursively and automatically uploads every archive produced by Objo Studio.

Supported archive formats include:

- `.tar.gz`
- `.tgz`
- `.zip`

Artifacts are renamed to include the application name and runtime identifier when appropriate.

Typical uploaded artifacts might look like:

```text
MyGreatApp-linux-x64.tar.gz
MyGreatApp-linux-arm64.tar.gz
```

---

## Example

```yaml
jobs:
  publish:
    uses: madamov/ObjoPublisher/.github/workflows/publish_objo_linux.yml@v1

    with:
      solution-file: MyGreatApp.objosln
      project-file: Projects/MyGreatApp/project.json
      application-name: MyGreatApp

      output-directory: Publish

      targets: "linux-x64"

      artifact-name: mygreatapp-linux

      # Optional
      # objo-version: "26.7.1"

    secrets:
      objo-license: ${{ secrets.OBJO_LICENSE }}
```

---

## Notes

- Linux publishing does not require platform-specific certificates.
- Multiple runtime identifiers can be published during a single workflow run.
- The latest Objo Studio release is used automatically unless a specific version is requested.
- The downloaded Objo Studio installation is cached by version.
- The Objo Studio license is automatically deactivated even if publishing fails.
- Every generated Linux archive is collected and uploaded automatically.

---

# publish_objo_windows.yml

Publishes one or more Windows applications created with Objo Studio and signs the generated MSIX packages using the official Azure Trusted Signing GitHub Action:

```text
azure/trusted-signing-action@v0
```

In this workflow, Objo Studio is responsible only for generating the MSIX packages. The Azure signing fields in `project.json` are cleared so that Objo does not attempt to invoke `signtool.exe` itself.

After publishing finishes, the reusable workflow signs all generated MSIX files using the Azure Trusted Signing action.

---

## Publishing process

```text
Checkout repository
        │
        ▼
Validate inputs
        │
        ▼
Determine Objo Studio version
        │
        ▼
Restore or download Objo Studio
        │
        ▼
Configure project.json for external signing
        │
        ▼
Activate Objo Studio license
        │
        ▼
Publish unsigned MSIX packages
        │
        ▼
Deactivate Objo Studio license
        │
        ▼
Sign MSIX packages using
azure/trusted-signing-action
        │
        ▼
Collect signed MSIX packages
        │
        ▼
Upload artifacts
```

---

## Workflow inputs

| Input | Required | Default | Description |
|--------|:-------:|---------|-------------|
| `solution-file` | ✔ | | Path to the Objo solution file. |
| `project-file` | ✔ | | Path to `project.json`. |
| `application-name` | ✔ | | Application name used when collecting artifacts and generating the default correlation ID. |
| `output-directory` | | `Publish` | Output directory under the current Windows user's home directory. |
| `targets` | | `win-x64` | Comma-separated list of Windows runtime identifiers. |
| `artifact-name` | | `objo-windows-publish` | Uploaded artifact name. |
| `objo-version` | | latest | Specific Objo Studio version to use. |
| `azure-correlation-id` | | generated | Optional Azure signing correlation ID. When omitted, a value based on the application name and GitHub run ID is generated. |

---

## Workflow secrets

| Secret | Required | Description |
|---------|:-------:|-------------|
| `objo-license` | ✔ | Objo Studio license key used during publishing. |
| `azure-tenant-id` | ✔ | Microsoft Entra tenant ID used by the Azure Trusted Signing action. |
| `azure-client-id` | ✔ | Application or service-principal client ID used to authenticate to Azure. |
| `azure-client-secret` | ✔ | Client secret associated with the Azure application registration. |
| `azure-endpoint` | ✔ | Azure Trusted Signing endpoint, for example `https://wus2.codesigning.azure.net/`. |
| `azure-account-name` | ✔ | Azure Trusted Signing account name. |
| `azure-certificate-profile-name` | ✔ | Trusted Signing certificate profile name. |
| `azure-package-publisher` | ✔ | Publisher value written into the MSIX manifest. It must match the publisher identity used by the signing certificate profile. |
| `azure-timestamp-url` | | Optional RFC 3161 timestamp server URL. When omitted, the signing action runs without timestamping. |

---

## External signing configuration

Before publishing, the workflow modifies the Windows signing section in `project.json`.

The Azure signing fields used by Objo are cleared:

```json
{
  "AzureEndpoint": "",
  "AzureAccountName": "",
  "AzureCertificateProfileName": "",
  "AzureCorrelationId": "",
  "TimestampUrl": ""
}
```

Only the package publisher remains populated:

```json
{
  "PackagePublisher": "CN=..."
}
```

This prevents Objo from attempting to sign the package locally with `signtool.exe` and `Azure.CodeSigning.Dlib.dll`.

The generated MSIX is then signed by:

```yaml
uses: azure/trusted-signing-action@v0
```

---

## Runtime identifiers

The workflow supports any Windows runtime identifier supported by Objo Studio.

Typical examples include:

| Runtime identifier | Platform |
|--------------------|----------|
| `win-x64` | 64-bit Intel/AMD Windows |
| `win-arm64` | ARM64 Windows |
| `win-x86` | 32-bit Windows |

Examples:

```yaml
with:
  targets: "win-x64"
```

or

```yaml
with:
  targets: "win-x64, win-arm64"
```

Whitespace around targets is removed automatically.

---

## Output directory

The default output directory is:

```text
%USERPROFILE%\Publish
```

On a GitHub-hosted Windows runner, this is typically similar to:

```text
C:\Users\runneradmin\Publish
```

It can be changed:

```yaml
with:
  output-directory: Documents\ObjoPublisher
```

which becomes:

```text
%USERPROFILE%\Documents\ObjoPublisher
```

Absolute Windows paths are also supported.

---

## Correlation ID

The correlation ID input is optional.

A caller can provide one explicitly:

```yaml
with:
  azure-correlation-id: "MyGreatApp-release-42"
```

When omitted, the workflow generates a value similar to:

```text
MyGreatApp-1234567890
```

where the numeric part is the GitHub Actions run ID.

The correlation ID is useful when reviewing Azure signing diagnostics and correlating a signing request with a specific GitHub Actions run.

---

## Timestamping

When `azure-timestamp-url` is provided, the workflow uses the timestamp-enabled signing step.

When the secret is empty or omitted, the workflow uses a second signing step that does not pass timestamp parameters to the Azure action.

This avoids supplying an empty `timestamp-rfc3161` value.

---

## Generated artifacts

The workflow searches the output directory recursively for `.msix` packages after signing.

The packages are copied into:

```text
%OUTPUT_DIRECTORY%\artifacts
```

and uploaded using `actions/upload-artifact`.

Typical uploaded packages might include:

```text
com.objo.app.mygreatapp_1.1.0.0_x64.msix
com.objo.app.mygreatapp_1.1.0.0_arm64.msix
```

If multiple packages have the same filename, the workflow adds information from the parent directory to prevent overwriting.

---

## Example

```yaml
name: ObjoPublisher for Windows

on:
  workflow_dispatch:

jobs:
  publish-windows:
    uses: madamov/ObjoPublisher/.github/workflows/publish_objo_windows.yml@v1

    with:
      solution-file: MyGreatApp.objosln
      project-file: Projects/MyGreatApp/project.json
      application-name: MyGreatApp

      output-directory: Publish
      targets: "win-x64"
      artifact-name: mygreatapp-windows

      # Optional
      # objo-version: "26.7.1"
      # azure-correlation-id: "MyGreatApp-${{ github.run_id }}"

    secrets:
      objo-license: ${{ secrets.OBJO_LICENSE }}

      azure-tenant-id: ${{ secrets.AZURE_TENANT_ID }}
      azure-client-id: ${{ secrets.AZURE_CLIENT_ID }}
      azure-client-secret: ${{ secrets.AZURE_CLIENT_SECRET }}

      azure-endpoint: ${{ secrets.AZURE_ENDPOINT }}
      azure-account-name: ${{ secrets.AZURE_ACCOUNTNAME }}
      azure-certificate-profile-name: ${{ secrets.AZURE_CERTIFICATEPROFILENAME }}
      azure-package-publisher: ${{ secrets.AZURE_PACKAGEPUBLISHER }}

      # Optional
      azure-timestamp-url: ${{ secrets.AZURE_TIMESTAMPURL }}
```

---

## Notes

- Objo Studio does not perform Windows signing in this workflow.
- Azure signing metadata is deliberately cleared from `project.json`.
- The package publisher is still written into the project because the MSIX manifest must contain the correct publisher identity.
- The official Azure Trusted Signing GitHub Action signs all generated MSIX packages recursively.
- The Objo Studio license is deactivated immediately after publishing.
- Multiple Windows targets are supported in one run.
- Objo Studio is cached by version.
- Timestamping is optional.

---

# publish_objo_windows_objosign.yml

Publishes one or more Windows applications created with Objo Studio and lets **Objo Studio perform Azure Trusted Signing** during the publish operation.

Unlike `publish_objo_windows.yml`, this workflow **does not** use the official Azure Trusted Signing GitHub Action.

Instead, it:

- installs the Microsoft Azure Artifact Signing Client Tools,
- locates `Azure.CodeSigning.Dlib.dll`,
- configures the Windows signing section in `project.json`,
- lets Objo invoke `signtool.exe`,
- and produces already signed MSIX packages.

This workflow is useful when you prefer Objo Studio to manage both publishing and signing.

---

## Publishing process

```text
Checkout repository
        │
        ▼
Validate inputs
        │
        ▼
Determine Objo Studio version
        │
        ▼
Restore or download Objo Studio
        │
        ▼
Install Azure Artifact Signing Client Tools
        │
        ▼
Locate Azure.CodeSigning.Dlib.dll
        │
        ▼
Configure Windows signing in project.json
        │
        ▼
Activate Objo Studio license
        │
        ▼
Publish and sign application
        │
        ▼
Deactivate license
        │
        ▼
Collect signed MSIX packages
        │
        ▼
Upload artifacts
```

---

## Workflow inputs

| Input | Required | Default | Description |
|--------|:-------:|---------|-------------|
| `solution-file` | ✔ | | Path to the Objo solution file. |
| `project-file` | ✔ | | Path to `project.json`. |
| `application-name` | ✔ | | Application name used when generating the default Azure correlation ID and naming artifacts. |
| `output-directory` | | `Publish` | Output directory under the current Windows user's home directory. |
| `targets` | | `win-x64` | Comma-separated list of Windows runtime identifiers. |
| `artifact-name` | | `objo-windows-signed-publish` | Uploaded artifact name. |
| `objo-version` | | latest | Specific Objo Studio version to use. |
| `azure-correlation-id` | | generated | Optional Azure correlation ID. When omitted, the workflow generates one automatically. |

---

## Workflow secrets

| Secret | Required | Description |
|---------|:-------:|-------------|
| `objo-license` | ✔ | Objo Studio license key. |
| `azure-endpoint` | ✔ | Azure Trusted Signing endpoint, for example `https://wus2.codesigning.azure.net/`. |
| `azure-account-name` | ✔ | Azure Trusted Signing account name. |
| `azure-certificate-profile-name` | ✔ | Azure Trusted Signing certificate profile name. |
| `azure-package-publisher` | ✔ | Publisher value written into the MSIX manifest. It must match the publisher configured in the Azure certificate profile. |
| `azure-timestamp-url` | | Optional RFC 3161 timestamp server URL. When omitted, Objo signs without timestamping. |

---

## Azure authentication

This workflow **does not require** Azure authentication credentials such as:

- Azure Tenant ID
- Azure Client ID
- Azure Client Secret

Objo Studio performs Azure Trusted Signing using Microsoft's Azure Artifact Signing Client Tools and the authentication mechanisms supported by those tools on the runner.

---

## Azure Artifact Signing Client Tools

Before publishing begins, the workflow installs Microsoft's **Azure Artifact Signing Client Tools** using `winget`.

After installation, it automatically searches several known installation locations to locate:

```text
Azure.CodeSigning.Dlib.dll
```

The discovered DLL path is exported as:

```text
AZURE_CODESIGNING_DLIB
```

allowing Objo Studio to invoke Azure Trusted Signing through Microsoft's signing library.

---

## Windows signing configuration

Before publishing, the workflow writes the Azure signing configuration into `project.json`.

The following values are configured:

- Azure Endpoint
- Azure Account Name
- Azure Certificate Profile Name
- Azure Correlation ID
- Timestamp URL
- Package Publisher

Because these values are present, Objo Studio automatically signs every generated MSIX package during publishing.

---

## Runtime identifiers

Typical runtime identifiers include:

| Runtime identifier | Platform |
|--------------------|----------|
| `win-x64` | 64-bit Windows |
| `win-arm64` | ARM64 Windows |
| `win-x86` | 32-bit Windows |

Examples:

```yaml
with:
  targets: "win-x64"
```

or

```yaml
with:
  targets: "win-x64, win-arm64"
```

Whitespace surrounding target names is ignored automatically.

---

## Correlation ID

The correlation ID is optional.

When not supplied, the workflow automatically generates one using:

- application name
- GitHub run ID
- GitHub run attempt

Example:

```text
MyGreatApp-1234567890-1
```

---

## Timestamping

Timestamping is optional.

If `azure-timestamp-url` is supplied, it is written into `project.json` and Objo requests timestamping while signing.

If omitted, the timestamp field is left empty and Objo signs without timestamping.

---

## Output directory

Default output directory:

```text
%USERPROFILE%\Publish
```

Typical GitHub-hosted runner location:

```text
C:\Users\runneradmin\Publish
```

Custom example:

```yaml
with:
  output-directory: Documents\Releases
```

Result:

```text
C:\Users\runneradmin\Documents\Releases
```

---

## Generated artifacts

After publishing completes, the workflow searches recursively for every generated `.msix` package.

The packages are copied into:

```text
artifacts
```

and uploaded using `actions/upload-artifact`.

Typical uploaded artifacts:

```text
com.objo.app.mygreatapp_1.1.0.0_x64.msix
com.objo.app.mygreatapp_1.1.0.0_arm64.msix
```

Duplicate filenames are renamed automatically to avoid overwriting.

---

## Example

```yaml
name: ObjoPublisher Windows (Objo Signing)

on:
  workflow_dispatch:

jobs:
  publish:
    uses: madamov/ObjoPublisher/.github/workflows/publish_objo_windows_objosign.yml@v1

    with:
      solution-file: MyGreatApp.objosln
      project-file: Projects/MyGreatApp/project.json
      application-name: MyGreatApp

      output-directory: Publish

      targets: "win-x64"

      artifact-name: mygreatapp-windows

      # Optional
      # objo-version: "26.7.1"
      # azure-correlation-id: "Release-42"

    secrets:
      objo-license: ${{ secrets.OBJO_LICENSE }}

      azure-endpoint: ${{ secrets.AZURE_ENDPOINT }}
      azure-account-name: ${{ secrets.AZURE_ACCOUNTNAME }}
      azure-certificate-profile-name: ${{ secrets.AZURE_CERTIFICATEPROFILENAME }}
      azure-package-publisher: ${{ secrets.AZURE_PACKAGEPUBLISHER }}

      # Optional
      azure-timestamp-url: ${{ secrets.AZURE_TIMESTAMPURL }}
```

---

## Differences from `publish_objo_windows.yml`

| Feature | `publish_objo_windows.yml` | `publish_objo_windows_objosign.yml` |
|---------|----------------------------|-------------------------------------|
| MSIX generation | Objo Studio | Objo Studio |
| MSIX signing | Azure Trusted Signing GitHub Action | Objo Studio |
| Azure Artifact Signing Client Tools | Not required | Installed automatically |
| `Azure.CodeSigning.Dlib.dll` | Not used | Located automatically |
| Azure Tenant / Client credentials | Required | Not required |
| `project.json` Azure settings | Cleared | Fully populated |
| Uses `azure/trusted-signing-action` | ✔ | ✘ |
| Objo invokes `signtool.exe` | ✘ | ✔ |

---

## Notes

- Objo Studio performs both publishing and signing.
- Microsoft's Azure Artifact Signing Client Tools are installed automatically.
- The workflow automatically locates `Azure.CodeSigning.Dlib.dll`.
- No additional signing step is required after publishing.
- The Objo Studio license is always deactivated before the workflow finishes.
- Objo Studio is cached by version.
- Multiple Windows runtime identifiers are supported.
- Timestamping is optional.

