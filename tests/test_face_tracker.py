from backend.services.face_tracker import (
    ensure_model,
    build_face_tracking_filter,
    track_clip_faces
)


def test_ensure_model_and_keyframes():
    has_model = ensure_model()
    assert isinstance(has_model, bool)

    # Empty / fallback keyframes
    keyframes = [(0.0, 0.5), (5.0, 0.5)]
    vf = build_face_tracking_filter(keyframes, ratio='9:16', layout='crop', resolution='1080p')
    assert 'scale=1080:1920' in vf
    assert 'crop=1080:1920' in vf

    # Multi-point tracking keyframes
    multi_kf = [(0.0, 0.35), (2.0, 0.40), (4.0, 0.65)]
    vf_dynamic = build_face_tracking_filter(multi_kf, ratio='9:16', layout='crop', resolution='1080p')
    assert 'scale=1080:1920' in vf_dynamic
    assert 'crop=1080:1920' in vf_dynamic
    assert 'if(lt(t' in vf_dynamic


def test_blur_layout_fallback():
    keyframes = [(0.0, 0.35), (2.0, 0.65)]
    vf_blur = build_face_tracking_filter(keyframes, ratio='9:16', layout='blur', resolution='1080p')
    assert 'boxblur' in vf_blur
