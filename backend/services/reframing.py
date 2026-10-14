RESOLUTION_SIZES = {
    '720p': {'9:16': (720, 1280), '1:1': (720, 720), '16:9': (1280, 720)},
    '1080p': {'9:16': (1080, 1920), '1:1': (1080, 1080), '16:9': (1920, 1080)},
    '4k': {'9:16': (2160, 3840), '1:1': (2160, 2160), '16:9': (3840, 2160)},
}
SIZES = RESOLUTION_SIZES['1080p']


def get_dimensions(ratio, resolution='1080p'):
    res_dict = RESOLUTION_SIZES.get(resolution, RESOLUTION_SIZES['1080p'])
    return res_dict.get(ratio, res_dict.get('9:16', (1080, 1920)))


def crop_filter(ratio, crop_x=50, resolution='1080p'):
    width, height = get_dimensions(ratio, resolution)
    position = max(0, min(100, crop_x)) / 100
    return f'scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos+accurate_rnd,crop={width}:{height}:(iw-ow)*{position}:(ih-oh)/2,cas=0.3,setsar=1'


def video_filter(ratio, layout='crop', crop_x=50, resolution='1080p', input_label='[0:v]'):
    """Return an FFmpeg filter graph preserving either a crop or the full original frame."""
    width, height = get_dimensions(ratio, resolution)
    if layout == 'blur':
        # Blur at reduced resolution, then upscale the backdrop; keep the foreground sharp with Lanczos + CAS.
        return (f'{input_label}split[back][front];'
                f'[back]scale={width//4}:{height//4}:force_original_aspect_ratio=increase:flags=bicubic,'
                f'crop={width//4}:{height//4},boxblur=12:2,scale={width}:{height}:flags=bicubic,setsar=1[bg];'
                f'[front]scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos+accurate_rnd,'
                f'cas=0.25,setsar=1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2')
    return input_label + crop_filter(ratio, crop_x, resolution)
