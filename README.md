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
