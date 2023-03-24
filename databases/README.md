# Piece Databases

## Architecture Overview
Pieces and their metadata are stored in SQLite databases. This is how the IDs (whatever LDraw and BrickLink use), names, and characteristics for pieces are recorded. We also store "categories" here, which define sets of pieces. For example, "tiles" might be a category, or "blue tiles," etc. This is also how the "sorting profiles" are saved. These are preset or user-defined and they tell the machine at runtime how it ought to actually sort the pieces (by color, by BrickLink category, every individual piece separated by kind and color?, and so on.) Sorting profiles can reference categories or individual kinds or colors in how they want pieces to be sorted.

*Note, because we're using SQLite, which is good for this type of embedded runtime environment, everything is actually stored as strings. Lists of tuples of strings are actually giant strings that need to be serialized and deserialized.

## LDraw
The primary source for what pieces exist, what they are, what their IDs are, and what they look like is the [LDraw Parts Library](https://www.ldraw.org/direct-parts-access). This contains `.dat` files which are like 3D CAD files representing LEGO® pieces. To obtain a textfile of all the available parts, `make` and run [the mklist from this fork](https://github.com/pybricks/ldraw/tree/master/mklist) of the parts library.

This will include all the slightly different versions of parts, every different print, minifig parts, and so on. When updating the `kinds` table, a parser only adds a fraction of the parts in the LDraw Parts Library list file for practicality reasons.

## BrickLink
While LDraw is the primary source for what parts exist, this is really only because you can't actually see every part available on BrickLink. We default to BrickLink for other metadata, like names, categories, and alternate IDs, and perhaps other stuff in the future like pictures and weight.

## Kinds
A kind is an abstract form a piece. Like 2x4 brick. It is not a realized piece, a real piece is a pair of `(kind, color)`. It has an ID, which is whatever the filename of its `.dat` in the parts library list file (a 2x4 brick has an ID `3001`), the name from the same file, and a list of manually added "characteristics", like `"['brick', '2 wide']".

## Colors
Pretty self-explanatory. The `colors` table has colors, and a color has an `id` and a `name`. We use the ones from BrickLink.

## Categories
Categories are reusable sets of pieces. They can contain specific pieces, which are pairs of `(kind, color)`, entire kinds regardless of color, entire colors, or other categories. So a category could be called "technic" whose only entries are in the "categories" column containing the keys for the "gears" and "technic bricks" categories. Then when a new gear is introduced, it's added to both the gears category and the technic category.

Every column is optional.

| category TEXT PRIMARY KEY | pieces TEXT (list of tuples `(kind, color)` of keys) | kinds TEXT (list of kind keys) | colors TEXT (list of color keys) | categories TEXT (list of category keys) |

## Profiles
Profiles are tables used at runtime to actually tell the machine which bins the user wants pieces to go to. They are essentially the same as categories, except there are meant to be many of them and they're user-customizable. While there is only one categories table, there will be many profiles.

| bin TEXT PRIMARY KEY | pieces TEXT (list of tuples `(kind, color)` of keys) | kinds TEXT (list of kind keys) | colors TEXT (list of color keys) | categories TEXT (list of category keys) |
