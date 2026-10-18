"""Analyze test_speech_duck.gd captures without changing production assets."""
import json
import math
from pathlib import Path

from analyze_rendered import loudness


def main():
    folder = Path('/tmp/firepower-duck')
    report = json.loads((folder / 'report.json').read_text(encoding='utf-8'))
    assert report['failures'] == 0
    layout_db = -0.0438385
    persisted_db = 20 * math.log10(0.7)
    report['master_gains_db'] = {'layout': layout_db, 'persisted_0.7': persisted_db}
    for row in report['renders']:
        path = folder / f"{row['raw']}_{str(row['duck']).lower()}_Master.f32"
        row['master_layout'] = loudness(path, report['mix_rate'], layout_db)
        row['master_persisted_0.7'] = loudness(path, report['mix_rate'], persisted_db)
    for name, target in [('attack_envelope', -8.0), ('release_envelope', -3.0)]:
        trace = report[name]
        report[name + '_first_observed_target_ms'] = next(x['ms'] for x in trace if abs(x['volume_db'] - target) < 0.001)
        values = [x['volume_db'] for x in trace]
        assert all((b <= a + 0.00001 if target == -8 else b >= a - 0.00001) for a, b in zip(values, values[1:]))
    destination = Path(__file__).with_name('duck_levels.json')
    destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(destination)
    print('Observed attack/release ms:', report['attack_envelope_first_observed_target_ms'], report['release_envelope_first_observed_target_ms'])
    for row in report['renders']:
        print(row['raw'], row['duck'], row['buses']['effects']['rms_dbfs_100_to_600ms'], row['master_persisted_0.7'])


if __name__ == '__main__':
    main()
