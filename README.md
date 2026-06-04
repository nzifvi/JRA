# WPSNN Architecture
## Neuron Lattice
WPSNN is organised into a neuron lattice that exists in a spherical coordinate system space, of radius R, segmented by rings. The origin neuron is (0, 0).
Each ring is defined using...
$$
r = i \cdot d
$$
Where $d$ is neuronSpacing and i is a natural number with bounded between [0, ceil(R/d)]

Arc-length scaling is used to determine the number of neurons to apply, per ring, to ensure uniform density across all rings. The number of neurons on ring r, N(r), is defined as...
$$
N(r) = ceil\bigg(\frac{2\pi r}{d}\bigg)
$$


# Propagation Diagnostics
## Import Details
Custom LIF model uses Euler integration whilst PyGenn LIF model uses exact exponential integration.

## Custom LIF vs PyGenn LIF Refactory Times
![Refactory Comparison](neuronFiringPlot.png)

## Wavefront Propagation

### PyGenn LIF
![PyGenn LIF](plotWithDefaultLIF.png)

### Custom LIF
![Custom LIF](plotWithCustomLIF.png)
