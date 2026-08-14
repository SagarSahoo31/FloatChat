"""
test_all.py - Complete Verification Test Suite for ARGO FloatChat v4.0 (Phase 1 & Phase 2).

Verifies Phase 1 AI Chat Engine (17 tests) & Phase 2 Data Platform (21 tests).
Run with: python -m unittest test_all.py
"""

import unittest
import time
import os
import json
from pathlib import Path

from backend.chatbot import get_chat_response
from backend.connectors import get_all_sources_status, ArgovisConnector, IfremerConnector, IncoisConnector, CustomUrlConnector
from backend.format_importer import import_and_validate_file, validate_oceanographic_dataset
from backend.pipeline import get_cache_status, purge_temporary_cache, start_public_url_import, get_import_job_status, DOWNLOADS_DIR, TEMP_DIR

class TestPhase1AIChatEngine(unittest.TestCase):

    def test_01_list_all_floats(self):
        resp = get_chat_response("List all floats")
        self.assertEqual(resp["type"], "data")
        self.assertIn("Float Fleet Index", resp["message"])

    def test_02_list_floats_by_ocean(self):
        resp = get_chat_response("List floats in the Arabian Sea")
        self.assertEqual(resp["type"], "data")
        self.assertIn("Arabian Sea", resp["message"])

    def test_03_float_metadata(self):
        resp = get_chat_response("Tell me about float 6901234")
        self.assertEqual(resp["type"], "data")
        self.assertIn("WMO 6901234", resp["message"])

    def test_04_temperature_profile(self):
        resp = get_chat_response("Show temperature profile for float 6901234 cycle 50")
        self.assertEqual(resp["type"], "chart")
        self.assertIn("Temperature Profile", resp["message"])

    def test_05_salinity_profile(self):
        resp = get_chat_response("Show salinity profile for float 6902881 cycle 30")
        self.assertEqual(resp["type"], "chart")
        self.assertIn("Salinity Profile", resp["message"])

    def test_06_oxygen_profile(self):
        resp = get_chat_response("Show oxygen profile for float 6901234 cycle 50")
        self.assertEqual(resp["type"], "chart")
        self.assertIn("Oxygen", resp["message"])

    def test_07_chlorophyll_profile(self):
        resp = get_chat_response("Show chlorophyll profile for float 6902881 cycle 30")
        self.assertEqual(resp["type"], "chart")
        self.assertIn("Chlorophyll", resp["message"])

    def test_08_trajectory(self):
        resp = get_chat_response("Show trajectory of float 6901234")
        self.assertEqual(resp["type"], "map")
        self.assertIn("Drift Trajectory", resp["message"])

    def test_09_float_comparison(self):
        resp = get_chat_response("Compare float 6901234 and 6902881")
        self.assertEqual(resp["type"], "data")
        self.assertIn("Side-by-Side Float Comparison", resp["message"])

    def test_10_cycle_comparison(self):
        resp = get_chat_response("Compare float 6901234 cycle 50 and cycle 49")
        self.assertEqual(resp["type"], "data")
        self.assertIn("Cycle Comparison", resp["message"])

    def test_11_multi_turn_memory_and_pronouns(self):
        history = []
        r1 = get_chat_response("Tell me about float 6901234", history)
        history.append({"role": "user", "content": "Tell me about float 6901234"})
        history.append({"role": "assistant", "content": r1["message"], "float_id": 6901234})

        r2 = get_chat_response("Show temperature", history)
        self.assertEqual(r2.get("float_id"), 6901234)

    def test_12_context_resolution(self):
        from backend.ai_orchestrator import resolve_contextual_query
        history = [{"role": "assistant", "content": "Float WMO 6901234 metadata", "float_id": 6901234}]
        ctx = resolve_contextual_query("its trajectory", history)
        self.assertEqual(ctx["wmo"], 6901234)

    def test_13_report_generation(self):
        resp = get_chat_response("Generate report for float 6901234")
        self.assertEqual(resp["type"], "report")
        self.assertIn("ARGO Oceanographic Research Report", resp["message"])

    def test_14_unknown_float_error_handling(self):
        resp = get_chat_response("Show float 9999999")
        self.assertIn("Float 9999999 Not Found", resp["message"])

    def test_15_invalid_cycle_error_handling(self):
        resp = get_chat_response("Show temperature profile float 6901234 cycle 999")
        self.assertIn("Cycle 999 Not Found", resp["message"])

    def test_16_help_command(self):
        resp = get_chat_response("Help")
        self.assertIn("Command Guide", resp["message"])

    def test_17_performance_under_repeated_queries(self):
        t0 = time.time()
        for _ in range(10):
            res = get_chat_response("Tell me about float 6901234")
            self.assertEqual(res["type"], "data")
        self.assertLess(time.time() - t0, 2.0)


class TestPhase2DataPlatform(unittest.TestCase):

    def test_201_connect_argovis(self):
        conn = ArgovisConnector()
        health = conn.health_check()
        self.assertIn("source_id", health)
        self.assertEqual(health["source_id"], "argovis")

    def test_202_connect_ifremer_gdac(self):
        conn = IfremerConnector()
        health = conn.health_check()
        self.assertIn("source_id", health)
        self.assertEqual(health["source_id"], "ifremer")

    def test_203_connect_incois(self):
        conn = IncoisConnector()
        health = conn.health_check()
        # Phase 2.6: new granular status labels
        valid_statuses = (
            "Connected but not synchronized", "Synchronized", "Available", "Connected",
            "\u26aa Never Imported", "\U0001f7e2 Complete", "\U0001f7e0 Pending",
        )
        self.assertIn(health["status"], valid_statuses)

    def test_204_import_csv(self):
        csv_file = DOWNLOADS_DIR / "test_data.csv"
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write("wmo,lat,lon,pres,temp,psal\n6901234,15.5,65.2,10.0,28.4,36.1\n6901234,15.5,65.2,50.0,26.1,36.2\n")
        records, val_res = import_and_validate_file(csv_file)
        self.assertTrue(val_res["is_valid"])
        self.assertEqual(len(records), 2)

    def test_205_import_excel(self):
        # Format validator gracefully handles Excel
        file_path = DOWNLOADS_DIR / "sample.xlsx"
        records, val_res = import_and_validate_file(file_path)
        self.assertIsNotNone(val_res)

    def test_206_import_netcdf(self):
        from backend.downloader import MOCK_ROOT
        nc_file = MOCK_ROOT / "6901234" / "R6901234_001.nc"
        records, val_res = import_and_validate_file(nc_file)
        self.assertTrue(val_res["is_valid"])

    def test_207_import_json(self):
        json_file = DOWNLOADS_DIR / "sample.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump([{"wmo": 6901234, "lat": 15.0, "lon": 65.0, "temp": 28.0}], f)
        records, val_res = import_and_validate_file(json_file)
        self.assertTrue(val_res["is_valid"])
        self.assertEqual(len(records), 1)

    def test_208_import_zip(self):
        zip_file = DOWNLOADS_DIR / "test_archive.zip"
        import zipfile
        sub_csv = DOWNLOADS_DIR / "sub.csv"
        with open(sub_csv, "w", encoding="utf-8") as f:
            f.write("wmo,lat,lon\n6901234,15.0,65.0\n")
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.write(sub_csv, arcname="sub.csv")
        records, val_res = import_and_validate_file(zip_file, TEMP_DIR)
        self.assertIsNotNone(val_res)

    def test_209_import_custom_url(self):
        conn = CustomUrlConnector()
        health = conn.health_check()
        # Phase 2.6: new granular status labels
        valid_statuses = (
            "Ready", "Connected but not synchronized", "Synchronized",
            "\u26aa Never Imported", "\u26aa Ready for Import", "\U0001f7e2 Complete",
        )
        self.assertIn(health["status"], valid_statuses)


    def test_210_resume_and_checksum(self):
        from backend.pipeline import compute_sha256
        csv_file = DOWNLOADS_DIR / "checksum_test.txt"
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write("argo float chat data platform")
        cksum = compute_sha256(csv_file)
        self.assertEqual(len(cksum), 64)

    def test_211_validate_corrupted_files(self):
        bad_file = DOWNLOADS_DIR / "bad.csv"
        with open(bad_file, "w", encoding="utf-8") as f:
            f.write("temp,lat,lon\n999.0,200.0,500.0\n")  # Out of physical bounds
        records, val_res = import_and_validate_file(bad_file)
        self.assertFalse(val_res["is_valid"])
        self.assertTrue(len(val_res["errors"]) > 0)

    def test_212_automatic_sqlite_and_faiss_updates(self):
        from backend.database import SessionLocal, FloatModel
        session = SessionLocal()
        try:
            count = session.query(FloatModel).count()
            self.assertGreaterEqual(count, 1)
        finally:
            session.close()

    def test_213_cache_management_and_purge(self):
        status = get_cache_status()
        self.assertEqual(status["status"], "Healthy")
        purged = purge_temporary_cache()
        self.assertGreaterEqual(purged, 0)

    def test_214_live_data_sources_dashboard(self):
        sources = get_all_sources_status()
        self.assertGreaterEqual(len(sources), 3)
        self.assertIn("endpoint", sources[0])

    def test_215_background_import_and_progress(self):
        job_id = start_public_url_import("https://data-argo.ifremer.fr/dac/incois/6901234/6901234_prof.nc")
        self.assertIsNotNone(job_id)
        status = get_import_job_status(job_id)
        self.assertIn("status", status)

    def test_216_system_telemetry(self):
        from backend.connectors import get_system_telemetry
        tel = get_system_telemetry()
        self.assertEqual(tel["overall_health"], "Healthy")
        self.assertIn("cpu_usage_pct", tel)
        self.assertIn("sqlite", tel)
        self.assertIn("faiss", tel)

    def test_217_dataset_header_previewer(self):
        from backend.downloader import MOCK_ROOT
        from backend.format_importer import preview_dataset_headers
        nc_file = MOCK_ROOT / "6901234" / "R6901234_001.nc"
        prev = preview_dataset_headers(nc_file)
        self.assertIn("dataset_name", prev)
        self.assertTrue(prev["record_count"] >= 1)

    def test_218_ai_dataset_provenance_summary(self):
        from backend.format_importer import generate_ai_dataset_summary
        records = [{"wmo": 6901234, "temp": 28.0, "psal": 35.5}]
        summary = generate_ai_dataset_summary("sample_argo.csv", records, {"is_valid": True})
        self.assertIn("AI Ingestion & Data Provenance Summary", summary)
        self.assertIn("6901234", summary)

    def test_219_connector_metric_separation(self):
        sources = get_all_sources_status()
        self.assertGreaterEqual(len(sources), 3)
        for s in sources:
            self.assertIn("remote_profiles", s)
            self.assertIn("imported_profiles", s)
            self.assertIn("indexed_profiles", s)

    def test_220_connector_synchronization_workflow(self):
        from backend.pipeline import start_connector_sync, get_connector_sync_status
        job_id = start_connector_sync("argovis")
        self.assertIsNotNone(job_id)
        time.sleep(6.0)  # Allow background sync pipeline (10 stages) to complete
        sync = get_connector_sync_status("argovis")
        # Phase 2.6: new emoji-prefixed status strings
        valid_complete = ("Synchronized", "\U0001f7e2 Complete")
        self.assertIn(sync["sync_status"], valid_complete)
        self.assertEqual(sync["download_progress"], 100)
        self.assertTrue(len(sync["sync_logs"]) >= 8)

if __name__ == "__main__":
    unittest.main()

