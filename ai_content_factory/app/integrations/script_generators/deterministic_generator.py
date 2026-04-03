from __future__ import annotations

from app.integrations.script_generators.base import GeneratedScriptPayload, ScriptGenerator
from app.models import ChannelConfig, TopicRecord


class DeterministicScriptGenerator(ScriptGenerator):
    provider_name = "deterministic_fallback"

    def generate(
        self,
        *,
        channel: ChannelConfig,
        topic: TopicRecord,
        prompt_template: str,
    ) -> GeneratedScriptPayload:
        subject = topic.topic.rstrip(".")
        hook, body_sentences = self._build_script(subject, channel)
        cta = self._build_cta(channel)
        return GeneratedScriptPayload(
            hook=hook,
            body=" ".join(body_sentences),
            cta=cta,
            provider_name=self.provider_name,
        )

    def _build_script(self, subject: str, channel: ChannelConfig) -> tuple[str, list[str]]:
        lowered = subject.lower()

        templates: list[tuple[tuple[str, ...], tuple[str, list[str]]]] = [
            (
                ("wi-fi", "wifi", "router", "signal"),
                (
                    "Your Wi-Fi gets slower at night.",
                    [
                        "More nearby devices wake up after dinner.",
                        "They crowd the same wireless channels.",
                        "Your router waits longer, so everything feels slower.",
                    ],
                ),
            ),
            (
                ("battery", "charge"),
                (
                    "Your battery drain is not random.",
                    [
                        "Background apps keep checking and syncing.",
                        "Heat and full charges wear the cell down.",
                        "Small settings changes can slow the damage.",
                    ],
                ),
            ),
            (
                ("smartphone", "phone", "iphone", "android"),
                (
                    "Your phone hides useful tools.",
                    [
                        "Most people never open the settings that matter.",
                        "A tiny shortcut can save taps every day.",
                        "That is why simple features feel like upgrades.",
                    ],
                ),
            ),
            (
                ("qr", "code", "codes"),
                (
                    "A QR code can still trick you.",
                    [
                        "The square hides the real web address.",
                        "A fake sticker can send you somewhere unsafe.",
                        "Always check the link before you trust it.",
                    ],
                ),
            ),
            (
                ("ai", "model", "prompt"),
                (
                    "Small AI tools save real time.",
                    [
                        "They handle repeat work in seconds.",
                        "That frees you for the part that needs judgment.",
                        "The win is speed, not magic.",
                    ],
                ),
            ),
            (
                ("history", "rome", "war", "castle", "map"),
                (
                    "One small detail changed this story.",
                    [
                        "The event looks simple from far away.",
                        "But one decision changed what happened next.",
                        "That twist is why people still remember it.",
                    ],
                ),
            ),
            (
                ("habit", "focus", "productivity", "mindset", "procrastinating"),
                (
                    "This habit works because it is small.",
                    [
                        "Big plans usually fail when life gets busy.",
                        "Tiny actions are easier to repeat every day.",
                        "That is how momentum quietly starts to grow.",
                    ],
                ),
            ),
        ]

        for keywords, template in templates:
            if any(keyword in lowered for keyword in keywords):
                return template

        if "tech" in channel.niche.lower() or "digital" in channel.niche.lower():
            return (
                "This tech detail changes the result.",
                [
                    "The problem looks random, but it has a pattern.",
                    "Once you spot the cause, the fix feels simpler.",
                    "That is why small settings create big results.",
                ],
            )

        return (
            f"{subject} makes more sense up close.",
            [
                "Most people only notice the surface.",
                "The useful part is the simple cause underneath it.",
                "Once you see that, the idea sticks faster.",
            ],
        )

    def _build_cta(self, channel: ChannelConfig) -> str:
        return channel.cta_template or "Follow for more tech facts."
