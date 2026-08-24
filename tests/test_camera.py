import warnings

import pytest

from texastoast.render.camera import Camera


def test_camera_default():
    cam = Camera(640, 480)
    assert cam.x == 0
    assert cam.y == 0
    assert cam.width == 640
    assert cam.height == 480


def test_camera_follow_center():
    cam = Camera(100, 100, smoothing=1.0)  # instant follow
    cam.follow(200, 200, map_width=500, map_height=500, dt=1 / 30)
    assert cam.x == 150.0
    assert cam.y == 150.0


def test_camera_clamp_to_map():
    cam = Camera(100, 100, smoothing=1.0)
    cam.follow(0, 0, map_width=200, map_height=200, dt=1 / 30)
    assert cam.x == 0
    assert cam.y == 0


def test_camera_clamp_right_edge():
    cam = Camera(100, 100, smoothing=1.0)
    cam.follow(500, 500, map_width=300, map_height=300, dt=1 / 30)
    assert cam.x == 200.0
    assert cam.y == 200.0


def test_camera_follow_without_dt_warns_but_still_works():
    # The no-dt path is deprecated (0.5.0 will require dt) but must keep the
    # old behaviour until then.
    cam = Camera(100, 100, smoothing=1.0)
    with pytest.warns(DeprecationWarning, match="dt"):
        cam.follow(200, 200, map_width=500, map_height=500)
    assert cam.x == 150.0


def test_camera_follow_with_dt_does_not_warn():
    cam = Camera(100, 100, smoothing=0.1)
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        cam.follow(200, 200, dt=1 / 30)


def test_camera_world_to_screen():
    cam = Camera(100, 100)
    cam.x = 50
    cam.y = 30
    sx, sy = cam.world_to_screen(100, 80)
    assert sx == 50.0
    assert sy == 50.0


def test_camera_screen_to_world():
    cam = Camera(100, 100)
    cam.x = 50
    cam.y = 30
    wx, wy = cam.screen_to_world(50, 50)
    assert wx == 100.0
    assert wy == 80.0


def test_camera_is_visible():
    cam = Camera(100, 100)
    cam.x = 50
    cam.y = 50
    assert cam.is_visible(60, 60, 10, 10) is True
    assert cam.is_visible(200, 200, 10, 10) is False
