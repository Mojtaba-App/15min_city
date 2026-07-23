# 15-Minute City Accessibility Project

## Overview
This project computes 15-minute pedestrian accessibility to key urban services using PostgreSQL, PostGIS, and pgRouting.

## Main Tables
- roads
- population_blocks
- urban_services

## Derived Outputs
- roads_vertices
- service_categories
- reachable_vertices_15min
- block_accessibility_15min
- v_block_accessibility_15min

## Accessibility Categories
- education
- health
- shopping
- recreation

## Accessibility Score
- 0 = no access
- 1 = one category
- 2 = two categories
- 3 = three categories
- 4 = full access
