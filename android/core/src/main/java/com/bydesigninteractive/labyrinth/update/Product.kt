// Which Labyrinth product an updater looks for on GitHub. The tag prefix and asset name are
// contracts with every installed copy, so a product's values never change once released.
package com.bydesigninteractive.labyrinth.update

data class Product(val tagPrefix: String, val assetName: String, val userAgent: String)

val TV_PRODUCT = Product("labyrinth-tv-v", "LabyrinthTV.apk", "Labyrinth-TV-updater")
val MOBILE_PRODUCT = Product("labyrinth-mobile-v", "LabyrinthMobile.apk", "Labyrinth-Mobile-updater")
