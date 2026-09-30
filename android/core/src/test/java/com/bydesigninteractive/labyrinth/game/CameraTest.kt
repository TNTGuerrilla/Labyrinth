package com.bydesigninteractive.labyrinth.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CameraTest {
    @Test
    fun fitFills80Percent() {
        val cam = Camera(20, 10, 1000, 500, coverage = 80)
        assertEquals(40, cam.fitPx)
        assertEquals(40, cam.cellPx)
        assertEquals(1.0, cam.zoom, 0.0)
        assertFalse(cam.zoomed)
    }

    @Test
    fun fitAtFullAndHalfCoverage() {
        assertEquals(50, Camera(20, 10, 1000, 500).fitPx)
        assertEquals(25, Camera(20, 10, 1000, 500, coverage = 50).fitPx)
    }

    @Test
    fun centeredAtFit() {
        assertEquals(100 to 50, Camera(20, 10, 1000, 500, coverage = 80).origin())
    }

    @Test
    fun zoomLimits() {
        val cam = Camera(20, 10, 1000, 500, coverage = 80)
        cam.zoomBy(100, 10.0 to 5.0)
        assertEquals(MAX_CELL_PX, cam.cellPx)
        cam.zoomBy(-100, 10.0 to 5.0)
        assertEquals(40, cam.cellPx)
    }

    @Test
    fun maxZoomNeverBelowFit() {
        val cam = Camera(2, 2, 1000, 1000, coverage = 80)
        assertEquals(400, cam.fitPx)
        cam.zoomBy(5, 1.0 to 1.0)
        assertEquals(400, cam.cellPx)
        assertEquals(400, cam.maxPx)
    }

    @Test
    fun zoomKeepsTheAnchorInPlace() {
        val cam = Camera(200, 100, 1000, 500, coverage = 80)
        val anchor = 37.5 to 20.5
        val before = cam.toScreen(anchor.first, anchor.second)
        cam.zoomBy(3, anchor)
        assertEquals(8, cam.cellPx)
        val after = cam.toScreen(anchor.first, anchor.second)
        assertEquals(before.first, after.first, 1.0)
        assertEquals(before.second, after.second, 1.0)
    }

    @Test
    fun zoomingBackToFitRecenters() {
        val cam = Camera(200, 100, 1000, 500, coverage = 80)
        cam.zoomBy(3, 37.5 to 20.5)
        cam.zoomBy(-10, 37.5 to 20.5)
        assertEquals(100.0, cam.cx, 0.0)
        assertEquals(50.0, cam.cy, 0.0)
        cam.zoomBy(3, 37.5 to 20.5)
        cam.resetZoom()
        assertFalse(cam.zoomed)
        assertEquals(100.0, cam.cx, 0.0)
    }

    @Test
    fun followConvergesOnTheDot() {
        val cam = Camera(200, 100, 1000, 500)
        cam.zoomBy(100, 100.0 to 50.0)
        repeat(100) { cam.follow(120.0 to 60.0, 0.1) }
        val (sx, sy) = cam.toScreen(120.0, 60.0)
        assertEquals(500.0, sx, 1.0)
        assertEquals(250.0, sy, 1.0)
    }

    @Test
    fun followStaysClampedNearAnEdge() {
        val cam = Camera(200, 100, 1000, 500)
        cam.zoomBy(100, 100.0 to 50.0)
        repeat(100) { cam.follow(1.0 to 1.0, 0.1) }
        assertEquals(0 to 0, cam.origin())
    }

    @Test
    fun followDoesNothingAtFit() {
        val cam = Camera(20, 10, 1000, 500, coverage = 80)
        cam.follow(0.5 to 0.5, 1.0)
        assertEquals(100 to 50, cam.origin())
    }

    @Test
    fun resizeKeepsTheZoomRatio() {
        val cam = Camera(100, 50, 1000, 500, coverage = 80)
        cam.zoomBy(1, 50.0 to 25.0)
        assertEquals(10, cam.cellPx)
        cam.resize(2000, 1000)
        assertEquals(16, cam.fitPx)
        assertEquals(20, cam.cellPx)
    }
}
