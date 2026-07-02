# Relevant Links
[Project Plan and Progress](https://trello.com/b/QE3CF7Dn/jra)

# Overview

# Biological Motivation

# Neuron Populations

## Egocentric Segment Neuron Populations

### PWo Neuron Population

### PWb Neuron Population

## Transformation Circuit Segment Neuron Populations

### GFTC Neuron Population

### HDC Neuron Population

## Allocentric Segment Neuron Populations

# Injection Mechanism
The injection mechanism, into both PWo and PWb populations, aims to inject a von Mises bump formatted injection, by means of a Gaussian kernel. This is described by a function that maps an input pixel $(x, y)$ which corresponds to a depth $d_{x,y}$ to a neuron with a preferred egocentric
azimuth $\theta_{e}(x)$, a preferred egocentric bearing $\phi_{e}(y)$, and a preferred distance $d_{x,y}$.

## Camera-based Inputs
The surrounding egocentric environment is scanned using a D445 camera. The sole channel used is the depth channel. The depth plane, $D$, can be modelled as a matrix, with $M$ height and $N$ width, where each pixel $(x', y')$ represents the recorded depth.

$$D_{M\times N} = \begin{bmatrix} d_{1,1} && ... && d_{1,N} \\\\ \vdots && \ddots && \vdots \\\\ d_{M,1} && ... && d_{M,N}\end{bmatrix}$$

The camera is mathematically modelled as a pinhole camera: giving...
1) Principal x-oridnate $p_x$
2) Principal y-ordinate $p_y$
3) Focal x-axis length $f_x$
4) Focal y-axis length $f_y$

A point in Cartesian space $(x, y, z)$ is mapped to the depth plane using the Camera. This is expressed as

$$x' = f_x \frac{x}{z}+p_x$$
$$y' = f_y \frac{y}{z} + p_y$$

Reversing this mapping (x' -> x) and (y' -> y) yields:

$$\frac{x}{z} = \frac{x' - p_x}{f_x}$$
$$\frac{y}{z} = \frac{y' - p_y}{f_y}$$

$$tan(\theta) = \frac{x}{z}$$
$$tan(\phi) = \frac{y}{z}$$

The azimuth angle, $\theta$, and the elevation angle, $\phi$, can be derived from the ratios ratios which have been themselves derived from the inverse mapping. This enables the cartesian-based
cooridnate system to be transformed into the required polar coordinate system the PWo and PWb neuron populations need.

$$\theta = tan^{-1}\bigg(\frac{x' - p_x}{f_x}\bigg)$$
$$\phi = tan^{-1}\bigg(\frac{y' - p_y}{f_y}\bigg)$$

## Handling of Depth-plane-neuron-population Resolution Mismatch
Due to the fact that the resolution of the depth plane and neuron population are not equivalent, a resolution mismatch exists between the two entities. Consequently, many pixels, from the depth plane, can map to a singular neuron in the population. 
