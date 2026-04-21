import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

if "psutil" not in sys.modules:
    sys.modules["psutil"] = types.SimpleNamespace(
        AccessDenied=RuntimeError,
        NoSuchProcess=RuntimeError,
        Process=object,
        process_iter=lambda *args, **kwargs: [],
    )

from chrome_ai_enabler import collect_profile_infos, inspect_preflight, patch_local_state


class PatchLocalStateTests(unittest.TestCase):
    def test_patch_local_state_enables_ai_and_switches_languages_to_english(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            user_data_path = Path(temp_dir)
            (user_data_path / "Last Version").write_text("146.0.0.0", encoding="utf-8")

            local_state = {
                "glic": {"is_glic_eligible": False, "launcher_enabled": False},
                "intl": {"app_locale": "zh-CN"},
                "profile": {"info_cache": {"Profile 1": {"is_glic_eligible": False}}},
                "variations_country": "cn",
                "variations_safe_seed_permanent_consistency_country": "cn",
                "variations_safe_seed_session_consistency_country": "sg",
                "variations_permanent_consistency_country": ["145.0.0.0", "cn"],
            }
            (user_data_path / "Local State").write_text(
                json.dumps(local_state, ensure_ascii=False),
                encoding="utf-8",
            )

            preferences_path = user_data_path / "Profile 1" / "Preferences"
            preferences_path.parent.mkdir(parents=True)
            preferences = {
                "intl": {
                    "accept_languages": "zh-CN,en-US,zh-TW,en",
                    "selected_languages": "zh-CN,zh-TW",
                }
            }
            preferences_path.write_text(
                json.dumps(preferences, ensure_ascii=False),
                encoding="utf-8",
            )

            result = patch_local_state("stable", user_data_path, "146.0.0.0")

            self.assertTrue(result.success)
            self.assertTrue(result.changed)

            updated_local_state = json.loads((user_data_path / "Local State").read_text(encoding="utf-8"))
            self.assertTrue(updated_local_state["glic"]["is_glic_eligible"])
            self.assertTrue(updated_local_state["profile"]["info_cache"]["Profile 1"]["is_glic_eligible"])
            self.assertEqual(updated_local_state["intl"]["app_locale"], "en")
            self.assertEqual(updated_local_state["variations_country"], "us")
            self.assertEqual(updated_local_state["variations_safe_seed_permanent_consistency_country"], "us")
            self.assertEqual(updated_local_state["variations_safe_seed_session_consistency_country"], "us")
            self.assertEqual(
                updated_local_state["variations_permanent_consistency_country"],
                ["146.0.0.0", "us"],
            )
            self.assertTrue(updated_local_state["glic"]["launcher_enabled"])

            updated_preferences = json.loads(preferences_path.read_text(encoding="utf-8"))
            self.assertEqual(updated_preferences["intl"]["accept_languages"], "en,zh-CN,zh-TW")
            self.assertEqual(updated_preferences["intl"]["selected_languages"], "en,zh-CN,zh-TW")
            self.assertTrue(updated_preferences["sync"]["glic_rollout_eligibility"])
            self.assertEqual(updated_preferences["browser"]["gemini_settings"], 0)
            self.assertTrue(updated_preferences["glic"]["pinned_to_tabstrip"])
            self.assertIn("Set Chrome UI locale to en", result.details)
            self.assertIn(
                "Moved English to the front of profile languages: Profile 1",
                result.details,
            )
            self.assertIn(
                "Forced rollout eligibility on profiles: Profile 1",
                result.details,
            )
            self.assertIn(
                "Forced Gemini settings policy to enabled: Profile 1",
                result.details,
            )
            self.assertIn(
                "Pinned Gemini button to tabstrip: Profile 1",
                result.details,
            )
    def test_preflight_detects_account_and_remote_status_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            user_data_path = Path(temp_dir)
            local_state = {
                "account_info": [],
                "glic": {"launcher_enabled": False},
                "intl": {"app_locale": "en"},
                "profile": {"info_cache": {"Default": {}}},
                "variations_country": "us",
                "variations_safe_seed_session_consistency_country": "sg",
            }
            (user_data_path / "Local State").write_text(
                json.dumps(local_state, ensure_ascii=False),
                encoding="utf-8",
            )

            preferences_path = user_data_path / "Default" / "Preferences"
            preferences_path.parent.mkdir(parents=True)
            preferences = {
                "browser": {"gemini_settings": 1},
                "glic": {"user_status": {"user_status": 2}},
                "sync": {"glic_rollout_eligibility": False},
            }
            preferences_path.write_text(
                json.dumps(preferences, ensure_ascii=False),
                encoding="utf-8",
            )

            report = inspect_preflight("stable", user_data_path)

            self.assertTrue(any("No signed-in Chrome profile detected" in item for item in report.blockers))
            self.assertTrue(any("remote status says disabled for this account/region" in item for item in report.blockers))
            self.assertTrue(any("glic_rollout_eligibility=false" in item for item in report.warnings))
            self.assertTrue(any("Session country signal is 'sg'" in item for item in report.warnings))

    def test_patch_local_state_can_target_one_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            user_data_path = Path(temp_dir)
            (user_data_path / "Last Version").write_text("146.0.0.0", encoding="utf-8")
            local_state = {
                "glic": {"launcher_enabled": False},
                "profile": {
                    "info_cache": {
                        "Default": {"is_glic_eligible": False},
                        "Profile 1": {"is_glic_eligible": False},
                    }
                },
                "variations_permanent_consistency_country": ["145.0.0.0", "cn"],
            }
            (user_data_path / "Local State").write_text(json.dumps(local_state), encoding="utf-8")

            for profile in ("Default", "Profile 1"):
                preferences_path = user_data_path / profile / "Preferences"
                preferences_path.parent.mkdir(parents=True)
                preferences_path.write_text(json.dumps({"intl": {"accept_languages": "zh-CN"}}), encoding="utf-8")

            result = patch_local_state("stable", user_data_path, "146.0.0.0", {"Profile 1"})

            self.assertTrue(result.success)
            updated_local_state = json.loads((user_data_path / "Local State").read_text(encoding="utf-8"))
            self.assertFalse(updated_local_state["profile"]["info_cache"]["Default"]["is_glic_eligible"])
            self.assertTrue(updated_local_state["profile"]["info_cache"]["Profile 1"]["is_glic_eligible"])

            default_preferences = json.loads((user_data_path / "Default" / "Preferences").read_text(encoding="utf-8"))
            profile_preferences = json.loads((user_data_path / "Profile 1" / "Preferences").read_text(encoding="utf-8"))
            self.assertNotIn("sync", default_preferences)
            self.assertTrue(profile_preferences["sync"]["glic_rollout_eligibility"])

    def test_collect_profile_infos_includes_profile_names_and_accounts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            user_data_path = Path(temp_dir)
            local_state = {
                "profile": {
                    "info_cache": {
                        "Default": {
                            "name": "Work",
                            "user_name": "work@example.com",
                            "gaia_name": "Work User",
                            "gaia_id": "123",
                        }
                    }
                }
            }
            (user_data_path / "Local State").write_text(json.dumps(local_state), encoding="utf-8")

            profiles = collect_profile_infos({"stable": user_data_path})

            self.assertEqual(len(profiles), 1)
            self.assertEqual(profiles[0].name, "Work")
            self.assertEqual(profiles[0].user_name, "work@example.com")
            self.assertEqual(profiles[0].directory, "Default")


if __name__ == "__main__":
    unittest.main()
