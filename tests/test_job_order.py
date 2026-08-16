import unittest

from app.schemas.base import JobEntry
from app.services.resume import restore_job_order


def make_job(job_id: str) -> JobEntry:
    return JobEntry(
        id=job_id,
        company=f"Company {job_id}",
        role="Engineer",
        start_date="2020",
        end_date="2024",
        bullets=[f"Bullet {job_id}"],
    )


class RestoreJobOrderTests(unittest.TestCase):
    def test_restores_input_order_after_model_reorders_jobs(self):
        input_jobs = [make_job("third"), make_job("first"), make_job("second")]
        generated_jobs = [make_job("first"), make_job("second"), make_job("third")]

        result = restore_job_order(generated_jobs, input_jobs)

        self.assertEqual([job.id for job in result], ["third", "first", "second"])

    def test_retains_unknown_ids_at_the_end_in_model_order(self):
        input_jobs = [make_job("second"), make_job("first")]
        generated_jobs = [
            make_job("unknown-a"),
            make_job("first"),
            make_job("unknown-b"),
            make_job("second"),
        ]

        result = restore_job_order(generated_jobs, input_jobs)

        self.assertEqual(
            [job.id for job in result],
            ["second", "first", "unknown-a", "unknown-b"],
        )


if __name__ == "__main__":
    unittest.main()
