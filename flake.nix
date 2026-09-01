{
  description = "MagNetFlix — Movie acquisition pipeline development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config = {
            allowUnfree = true;
          };
        };
      in
      {
        devShells.default = pkgs.mkShell {
          name = "magnetflix-dev-shell";

          nativeBuildInputs = with pkgs; [
            buf
            gnumake
            pkg-config
          ];

          buildInputs = with pkgs; [
            # Python & package management
            python312
            uv

            # Local torrent daemon for dev/testing
            transmission_4

            # Database tooling
            sqlite

            # Container tooling
            docker-compose
          ];

          shellHook = ''
            echo "🎬 Entering MagNetFlix DevShell"
            echo "  • Python:       $(python3 --version)"
            echo "  • UV:           $(uv --version)"
            echo "  • Buf:          $(buf --version)"
            echo "  • Transmission: $(transmission-daemon --version 2>&1 | head -n 1)"

            # Automatically sync uv workspace if .venv is missing
            if [ ! -d ".venv" ]; then
              echo "Creating virtual environment and syncing workspace..."
              uv sync
            fi
          '';
        };
      }
    );
}
