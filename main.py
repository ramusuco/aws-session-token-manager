import pyotp
import os
from dataclasses import dataclass
import cattrs, json
import subprocess
import configparser
from dataclasses import replace


@dataclass(frozen=True)
class profiles:
    profile_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    mfa_secret: str
    serial: str
    region: str
    default: bool = False


@dataclass
class settings_json:
    aws_credential_path: str
    profiles: list[profiles]


def load_settings() -> settings_json:
    F = "settings.json"
    json_open = open(F, "r")
    json_load = json.load(json_open)
    settings = cattrs.structure(json_load, settings_json)
    return settings


def set_env(profile: profiles):
    os.environ["AWS_ACCESS_KEY_ID"] = profile.aws_access_key_id
    os.environ["AWS_SECRET_ACCESS_KEY"] = profile.aws_secret_access_key
    os.environ["AWS_DEFAULT_REGION"] = profile.region


def get_session_token(profile: profiles) -> subprocess.CompletedProcess:
    set_env(profile)
    cmd = f"aws sts get-session-token --serial-number {profile.serial} --token-code {pyotp.TOTP(profile.mfa_secret).now()} --output json"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res


def format_credentials(session_json: dict) -> dict:
    return {
        "aws_access_key_id": session_json["AccessKeyId"],
        "aws_secret_access_key": session_json["SecretAccessKey"],
        "aws_session_token": session_json["SessionToken"],
    }


def main():
    settings = load_settings()
    config = configparser.ConfigParser()
    for profile in settings.profiles:
        print(profile.profile_name)
        res = get_session_token(profile)
        session_json = json.loads(res.stdout)["Credentials"]
        if profile.default:
            config["default"] = format_credentials(session_json)
        config[profile.profile_name] = format_credentials(session_json)

    with open(settings.aws_credential_path, "w") as f:
        config.write(f)


if __name__ == "__main__":
    main()
