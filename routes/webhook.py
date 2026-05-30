# routes/webhook.py
import hashlib
import hmac
import logging
import os
import subprocess
from flask import Blueprint, request, abort

webhook_bp = Blueprint("webhook", __name__)


def _deploy_app_dir() -> str:
    return os.getenv("DEPLOY_APP_DIR", "/var/www/pokeAPI")


@webhook_bp.route("/webhook/", methods=["POST", "GET"])
def webhook():
    secret = os.getenv("WEBHOOK_SECRET")

    if request.method == "POST":
        # Verify the webhook secret is set
        if secret is None:
            logging.error("Webhook secret is not configured")
            abort(500, "Webhook secret is not configured")

        # Verify the signature from GitHub
        signature = request.headers.get("X-Hub-Signature-256")
        if signature is None:
            logging.error("No signature provided")
            abort(403, "No signature provided")

        sha_name, signature_from_github = signature.split("=")
        if sha_name != "sha256":
            logging.error(f"Signature type '{sha_name}' is not supported")
            abort(501, "Signature type not supported")

        # Calculate the expected signature
        mac = hmac.new(
            bytes(secret, "utf-8"), msg=request.data, digestmod=hashlib.sha256
        )
        generated_signature = mac.hexdigest()

        # Compare the generated signature with the one from GitHub
        if not hmac.compare_digest(generated_signature, signature_from_github):
            logging.error("Invalid signature - Signatures do not match")
            abort(403, "Invalid signature")

        # Pull the latest changes from the repository
        try:
            # First stash any local changes - use 'git stash -u' to include untracked files
            # and redirect stderr to stdout to capture all output
            stash_result = subprocess.run(
                ["git", "-C", _deploy_app_dir(), "stash", "-u", "--include-untracked"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            logging.info("Git stash output: " + stash_result.stdout)

            # Check if anything was stashed
            was_stashed = "No local changes to save" not in stash_result.stdout

            # Then pull the new changes
            result = subprocess.run(
                ["git", "-C", _deploy_app_dir(), "pull"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logging.info("Git pull output: " + result.stdout)

            # Only drop the stash if something was actually stashed
            if was_stashed:
                drop_result = subprocess.run(
                    ["git", "-C", _deploy_app_dir(), "stash", "drop"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                logging.info("Git stash drop output: " + drop_result.stdout)
            else:
                logging.info("No stash to drop - nothing was stashed")
        except subprocess.CalledProcessError as e:
            logging.error(f"Git command failed: {e.stderr}")
            abort(500, f"Git command failed: {str(e)}")

        # Activate virtual environment and install requirements
        try:
            # Construct the command to source the virtual environment and install requirements
            activate_and_install = [
                "/bin/bash",
                "-c",
                ". {}/venv/bin/activate && cd {} && pip install -r requirements.txt".format(
                    _deploy_app_dir(), _deploy_app_dir()
                ),
            ]

            result = subprocess.run(
                activate_and_install,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logging.info(f"Requirements installation output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Requirements installation failed: {e.stderr}")
            abort(500, f"Requirements installation failed: {str(e)}")

        # Restart Gunicorn using sudo with timeout
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "restart", "gunicorn"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,  # Timeout after 30 seconds
            )

            # Check if the return code is -15 (SIGTERM)
            if result.returncode == -15:
                logging.debug(
                    "Gunicorn restart returned SIGTERM (-15), but continuing as restart succeeded."
                )
            else:
                logging.info(f"Gunicorn restart output: {result.stdout}")

        except subprocess.CalledProcessError as e:
            # Ignore if the return code is -15 (SIGTERM) since Gunicorn restarts successfully
            if e.returncode == -15:
                logging.debug(
                    f"Gunicorn restart received SIGTERM (-15), but this is expected. Continuing."
                )
            else:
                logging.error(
                    f"Gunicorn restart failed with return code {e.returncode}: {e.stderr}"
                )
                abort(500, f"Gunicorn restart failed: {str(e)}")
        except subprocess.TimeoutExpired as e:
            logging.error(f"Gunicorn restart timed out: {e}")
            abort(500, "Gunicorn restart timed out.")

        return "Success", 200

    elif request.method == "GET":
        logging.info("GET request received - Returning 403 Forbidden")
        return "Forbidden", 403
