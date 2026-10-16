"""Presentation helpers; no changes to forecast or inventory mathematics."""
import re


def evidence_stamps(root, run_id, parent_id):
    """Invalidate the UI cache if either sealed bundle or receipt changes."""
    if not all(re.fullmatch(r'[A-Za-z0-9_-]+', name) for name in [run_id, parent_id]):
        raise ValueError('Invalid evidence run')
    output = root / 'outputs'
    paths = []
    for name in [run_id, parent_id]:
        folder = output / name
        if not folder.is_dir():
            raise FileNotFoundError('Missing result bundle')
        paths.extend(p for p in folder.rglob('*') if p.is_file())
        paths.append(output / (name + '_verification.json'))
    return tuple((p.relative_to(output).as_posix(), p.stat().st_size, p.stat().st_mtime_ns)
        for p in sorted(paths))


def recommendation_action(row):
    if row['on_hand'] <= 0:
        return 'Hết hàng · ưu tiên xử lý'
    if row['Q'] > 0:
        return 'Xem xét đặt bổ sung'
    if row['needs_replenishment']:
        return 'Đã có hàng đang về · theo dõi ETA'
    return 'Theo dõi định kỳ'
