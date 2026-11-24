"""Both connection-monitor examples must work with the reported sensor state."""
from pathlib import Path
import re

import pytest
import yaml
from homeassistant.helpers import config_validation as cv


@pytest.mark.parametrize("readme", ["README.md", "README.de.md"])
def test_offline_notification_example(readme):
    text = (Path(__file__).parents[1] / readme).read_text()
    example, = (
        yaml.safe_load(block)["automation"][0]
        for block in re.findall(r"```yaml\n(.*?)\n```", text, re.DOTALL)
        if block.startswith("automation:\n")
    )
    trigger, = example["trigger"]
    entity_id = trigger["entity_id"]
    assert entity_id.startswith("binary_sensor.") and cv.entity_id(entity_id) == entity_id
    assert trigger["platform"] == "state" and trigger["to"] == "off"
    assert cv.time_period(trigger["for"]).total_seconds() == 60
    assert example["action"][0]["service"] == "persistent_notification.create"
