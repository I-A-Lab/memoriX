from __future__ import annotations

import unittest

from memory.adaptive import (
    TopicBlockInput,
    build_topic_block_id,
    calculate_routing_confidence,
    extract_topic_terms,
    normalize_topic_term,
    observe_topic_block,
    select_topic_label,
)


class TermNormalizationTests(unittest.TestCase):
    def test_accents_are_normalized(self) -> None:
        self.assertEqual(
            normalize_topic_term("Mémoire"),
            "memoire",
        )

    def test_punctuation_is_removed(self) -> None:
        self.assertEqual(
            normalize_topic_term("Titan!"),
            "titan",
        )


class TermExtractionTests(unittest.TestCase):
    def test_terms_are_extracted_dynamically(
        self,
    ) -> None:
        terms = extract_topic_terms(
            (
                "Titan neural retrieval uses "
                "validated external memories. "
                "Titan retrieval remains hot-only."
            )
        )

        names = [
            term.term
            for term in terms
        ]

        self.assertIn("titan", names)
        self.assertIn("retrieval", names)
        self.assertIn("validated", names)

    def test_metadata_terms_receive_weight(
        self,
    ) -> None:
        terms = extract_topic_terms(
            "A discussion about several systems.",
            metadata_terms=(
                "astronomy",
                "astronomy",
            ),
        )

        self.assertEqual(
            terms[0].term,
            "astronomy",
        )
        self.assertGreaterEqual(
            terms[0].count,
            4,
        )

    def test_noise_only_content_has_no_terms(
        self,
    ) -> None:
        terms = extract_topic_terms(
            "le la les de des et ou"
        )

        self.assertEqual(terms, ())

    def test_order_is_deterministic(self) -> None:
        first = extract_topic_terms(
            "beta alpha gamma beta alpha"
        )
        second = extract_topic_terms(
            "beta alpha gamma beta alpha"
        )

        self.assertEqual(first, second)


class DynamicLabelTests(unittest.TestCase):
    def test_label_uses_strongest_term(self) -> None:
        terms = extract_topic_terms(
            "music music guitar melody"
        )

        self.assertEqual(
            select_topic_label(terms),
            "music",
        )

    def test_empty_terms_use_neutral_fallback(
        self,
    ) -> None:
        self.assertEqual(
            select_topic_label(()),
            "unclassified",
        )

    def test_block_id_is_deterministic(self) -> None:
        self.assertEqual(
            build_topic_block_id("Astronomie"),
            "block_astronomie",
        )


class RoutingConfidenceTests(unittest.TestCase):
    def test_single_term_is_clear(self) -> None:
        terms = extract_topic_terms(
            "astronomy astronomy astronomy"
        )

        self.assertEqual(
            calculate_routing_confidence(terms),
            1.0,
        )

    def test_empty_terms_have_zero_confidence(
        self,
    ) -> None:
        self.assertEqual(
            calculate_routing_confidence(()),
            0.0,
        )


class TopicBlockObservationTests(unittest.TestCase):
    def test_observation_is_action_free(self) -> None:
        observation = observe_topic_block(
            TopicBlockInput(
                content=(
                    "Astronomy telescope stars "
                    "astronomy observation."
                ),
                item_id="item_astronomy",
                metadata_terms=(
                    "space",
                ),
                importance=0.8,
                capacity=100,
                used_items=1,
                observed_at=(
                    "2026-07-14T10:00:00+00:00"
                ),
            ),
            routing_id="routing_test",
        )

        self.assertTrue(
            observation.observation_only
        )
        self.assertTrue(
            observation.routing.observation_only
        )
        self.assertEqual(
            observation.observed_item_ids,
            ("item_astronomy",),
        )
        self.assertEqual(
            observation.routing.routing_id,
            "routing_test",
        )
        self.assertEqual(
            observation.used_items,
            1,
        )
        self.assertEqual(
            observation.capacity,
            100,
        )
        self.assertEqual(
            observation.usage_ratio,
            0.01,
        )
        self.assertTrue(
            any(
                "No candidate" in line
                for line in (
                    observation.routing.explanation
                )
            )
        )

    def test_observation_is_deterministic_except_ids(
        self,
    ) -> None:
        source = TopicBlockInput(
            content=(
                "guitar melody guitar concert"
            ),
            item_id="item_music",
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
        )

        first = observe_topic_block(
            source,
            routing_id="routing_fixed",
        )
        second = observe_topic_block(
            source,
            routing_id="routing_fixed",
        )

        self.assertEqual(
            first.to_dict(),
            second.to_dict(),
        )

    def test_invalid_input_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            observe_topic_block(
                TopicBlockInput(
                    content="",
                    item_id="item_test",
                )
            )


if __name__ == "__main__":
    unittest.main()
