import operator

import numpy as np


def _finite_array(values, dimensions, name):
    if np.iscomplexobj(values):
        raise ValueError(f"{name} must contain real values")
    array = np.asarray(values, dtype=float)
    if array.ndim != dimensions or array.size == 0 or not np.isfinite(array).all():
        raise ValueError(f"{name} must be a nonempty, finite {dimensions}D array")
    return array


def generate_fringes(phase, n_steps=5, *, noise_std=0.0, phase_drift=0.0, seed=0):
    """Return N float images; phase and inter-frame drift are in radians.

    Intensity is 0.5 + 0.4*cos(phase + step + drift), plus Gaussian noise.
    Values are not clipped or quantised. Drift accumulates from frame zero.
    """
    phase = _finite_array(phase, 2, "phase")
    try:
        n_steps = operator.index(n_steps)
    except TypeError as error:
        raise ValueError("n_steps must be an integer of at least 3") from error
    if n_steps < 3:
        raise ValueError("n_steps must be an integer of at least 3")
    if not np.isfinite(noise_std) or noise_std < 0:
        raise ValueError("noise_std must be finite and nonnegative")
    if not np.isfinite(phase_drift):
        raise ValueError("phase_drift must be finite")
    indices = np.arange(n_steps)[:, None, None]
    shifts = indices * (2 * np.pi / n_steps + phase_drift)
    images = 0.5 + 0.4 * np.cos(phase[None, :, :] + shifts)
    if noise_std:
        images += np.random.default_rng(seed).normal(0, noise_std, images.shape)
    return images


def recover_phase(images, min_modulation=1e-6):
    """Return wrapped phase (radians) and estimated modulation amplitude.

    Frames must use equally spaced nominal steps over one full turn.
    Reject the whole stack if any pixel has insufficient modulation.
    """
    images = _finite_array(images, 3, "images")
    n_steps = images.shape[0]
    if n_steps < 3:
        raise ValueError("at least three images are required")
    if not np.isfinite(min_modulation) or min_modulation <= 0:
        raise ValueError("min_modulation must be finite and positive")
    shifts = 2 * np.pi * np.arange(n_steps)[:, None, None] / n_steps
    cosine = np.sum(images * np.cos(shifts), axis=0)
    sine = np.sum(images * np.sin(shifts), axis=0)
    modulation = 2 * np.hypot(cosine, sine) / n_steps
    if np.any(modulation < min_modulation):
        raise ValueError("insufficient modulation at one or more pixels")
    return np.arctan2(-sine, cosine), modulation


def unwrap_phase(wrapped):
    """Unwrap rows, then columns; assumes smooth phase without invalid pixels.

    True neighbouring phase differences must stay below pi. This cannot
    recover the unknown global multiple of 2*pi or resolve discontinuities.
    """
    wrapped = _finite_array(wrapped, 2, "wrapped phase")
    return np.unwrap(np.unwrap(wrapped, axis=1), axis=0)
