import numpy as np
import pytest

from phase_demo.core import generate_fringes, recover_phase, unwrap_phase


def test_four_hand_calculated_pixels_preserve_all_phase_quadrants():
    images = np.array([[3, 1, 1, 3], [1, 1, 3, 3], [1, 3, 3, 1], [3, 3, 1, 1]])[:, None, :]
    wrapped, modulation = recover_phase(images)
    np.testing.assert_allclose(wrapped, [[np.pi / 4, 3 * np.pi / 4, -3 * np.pi / 4, -np.pi / 4]])
    np.testing.assert_allclose(modulation, np.sqrt(2))


def test_zero_phase_produces_the_expected_four_intensities():
    images = generate_fringes([[0]], n_steps=4)
    np.testing.assert_allclose(images[:, 0, 0], [0.9, 0.5, 0.1, 0.5])


@pytest.mark.parametrize("n_steps", [3, 5, 8])
def test_smooth_ramp_is_recovered_across_both_axes_up_to_one_turn(n_steps):
    y, x = np.mgrid[0:24, 0:32]
    truth = 3.4 + 0.3 * x + 0.4 * y
    wrapped, modulation = recover_phase(generate_fringes(truth, n_steps))
    np.testing.assert_allclose(unwrap_phase(wrapped), truth - 2 * np.pi, atol=1e-12)
    np.testing.assert_allclose(modulation, 0.4, atol=1e-12)


@pytest.mark.parametrize(
    "images",
    [np.zeros((2, 2, 2)), np.zeros((3, 0, 2)), np.full((3, 2, 2), np.nan), np.ones((3, 2, 2), complex)],
    ids=["too-few-frames", "empty-image", "non-finite", "complex"],
)
def test_invalid_image_stacks_are_rejected(images):
    with pytest.raises(ValueError):
        recover_phase(images)


def test_a_pixel_without_modulation_rejects_the_stack():
    images = generate_fringes([[0, 0.2]])
    images[:, 0, 1] = 0.5
    with pytest.raises(ValueError, match="insufficient modulation"):
        recover_phase(images)


@pytest.mark.parametrize(
    "settings",
    [{"n_steps": 2}, {"noise_std": -0.1}, {"phase_drift": np.inf}],
)
def test_invalid_synthesis_settings_are_rejected(settings):
    with pytest.raises(ValueError):
        generate_fringes([[0]], **settings)
