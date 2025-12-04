#!/usr/bin/env python3
"""Deploy MCP Cloud Server to Google Cloud Run."""

import subprocess
import sys
import argparse


def run_command(command: list[str], description: str) -> bool:
    """Run a shell command and return success status."""
    print(f"\n{'='*60}")
    print(f">>> {description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(command)}\n")

    result = subprocess.run(command)

    if result.returncode != 0:
        print(f"\nError: {description} failed with exit code {result.returncode}")
        return False

    print(f"\n{description} completed successfully.")
    return True


def deploy(
    project_id: str,
    region: str = "us-central1",
    service_name: str = "mcp-server",
    allow_unauthenticated: bool = True,
    skip_build: bool = False,
) -> bool:
    """Deploy the MCP server to Google Cloud Run.

    Args:
        project_id: Google Cloud project ID
        region: GCP region for deployment
        service_name: Name of the Cloud Run service
        allow_unauthenticated: Whether to allow public access
        skip_build: Skip building and just deploy existing image

    Returns:
        True if deployment succeeded, False otherwise
    """
    image_url = f"gcr.io/{project_id}/{service_name}"

    # Step 1: Build and push container image
    if not skip_build:
        build_command = [
            "gcloud", "builds", "submit",
            "--tag", image_url,
            "--project", project_id,
        ]

        if not run_command(build_command, "Building container image"):
            return False

    # Step 2: Deploy to Cloud Run
    deploy_command = [
        "gcloud", "run", "deploy", service_name,
        "--image", image_url,
        "--platform", "managed",
        "--region", region,
        "--project", project_id,
    ]

    if allow_unauthenticated:
        deploy_command.append("--allow-unauthenticated")

    if not run_command(deploy_command, "Deploying to Cloud Run"):
        return False

    # Step 3: Get service URL
    url_command = [
        "gcloud", "run", "services", "describe", service_name,
        "--platform", "managed",
        "--region", region,
        "--project", project_id,
        "--format", "value(status.url)",
    ]

    print(f"\n{'='*60}")
    print(">>> Getting service URL")
    print(f"{'='*60}")

    result = subprocess.run(url_command, capture_output=True, text=True)

    if result.returncode == 0 and result.stdout.strip():
        service_url = result.stdout.strip()
        print(f"\nDeployment successful!")
        print(f"\n{'='*60}")
        print("SERVICE DETAILS")
        print(f"{'='*60}")
        print(f"Service URL: {service_url}")
        print(f"SSE Endpoint: {service_url}/sse")
        print(f"\nTest with MCP Inspector:")
        print(f"  npx @modelcontextprotocol/inspector \\")
        print(f"      npx -y @modelcontextprotocol/server-sse-client \\")
        print(f"      --url {service_url}/sse")
        print(f"{'='*60}\n")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Deploy MCP Cloud Server to Google Cloud Run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy with project ID
  python gcp_deploy.py --project-id my-project-123

  # Deploy to specific region with custom service name
  python gcp_deploy.py --project-id my-project-123 --region europe-west1 --service-name weather-mcp

  # Redeploy without rebuilding
  python gcp_deploy.py --project-id my-project-123 --skip-build
        """,
    )

    parser.add_argument(
        "--project-id", "-p",
        required=True,
        help="Google Cloud project ID",
    )
    parser.add_argument(
        "--region", "-r",
        default="us-central1",
        help="GCP region for deployment (default: us-central1)",
    )
    parser.add_argument(
        "--service-name", "-s",
        default="mcp-server",
        help="Cloud Run service name (default: mcp-server)",
    )
    parser.add_argument(
        "--no-allow-unauthenticated",
        action="store_true",
        help="Require authentication to access the service",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip building container, deploy existing image",
    )

    args = parser.parse_args()

    success = deploy(
        project_id=args.project_id,
        region=args.region,
        service_name=args.service_name,
        allow_unauthenticated=not args.no_allow_unauthenticated,
        skip_build=args.skip_build,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
