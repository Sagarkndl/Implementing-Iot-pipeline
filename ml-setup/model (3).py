"""
╔══════════════════════════════════════════════════════════╗
║              ExamModel — Self-Contained                  ║
║                                                          ║
║  Change the CONFIG section below, then just run:        ║
║    python model.py                                       ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


DATASET = "mnist"

# ── Folder paths (only used when DATASET = "folder_*") ────
TRAIN_PATH  = "data/train"     # used with "folder_split"
VAL_PATH    = "data/valid"     # used with "folder_split"
TEST_PATH   = "data/test"      # used with "folder_split"
SINGLE_PATH = "data"           # used with "folder_auto"

# ── Folder auto-split ratios (must sum to 100) 
TRAIN_PCT = 70
VAL_PCT   = 15
TEST_PCT  = 15

# ── Image settings 
IMAGE_SIZE = (64, 64)    # (H, W) — built-in datasets ignore this

# ── Training settings
EPOCHS     = 30
BATCH_SIZE = 64
SAVE_PATH  = "exam_model.keras"


# 
# ║                    DO NOT EDIT BELOW                     


SUPPORTED_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif")



#  FOLDER LOADER


def load_folder(path: str, image_size: tuple, classes: list = None) -> tuple:
    """
    Load all images from a directory of class sub-folders.

    Structure:
        path/
            class_a/  img1.jpg  img2.png ...
            class_b/  img1.jpg  ...

    Returns: (images: float32 array, labels: int array, class_names: list)
    """
    if not os.path.isdir(path):
        raise FileNotFoundError(
            f"\n[ERROR] Folder not found: '{path}'\n"
            f"  Make sure the path exists and contains class sub-folders.\n"
            f"  Example structure:\n"
            f"    {path}/cat/img1.jpg\n"
            f"    {path}/dog/img1.jpg\n"
        )

    if classes is None:
        classes = sorted([
            d for d in os.listdir(path)
            if os.path.isdir(os.path.join(path, d)) and not d.startswith(".")
        ])

    if len(classes) == 0:
        raise ValueError(
            f"\n[ERROR] No class sub-folders found in '{path}'.\n"
            f"  Each class must be its own sub-folder.\n"
        )

    print(f"  Folder : {path}")
    print(f"  Classes: {classes}")

    images, labels = [], []
    for idx, cls in enumerate(classes):
        cls_folder = os.path.join(path, cls)
        if not os.path.isdir(cls_folder):
            print(f"  [WARN] '{cls}' not found in {path}, skipping.")
            continue
        files = [
            f for f in os.listdir(cls_folder)
            if f.lower().endswith(SUPPORTED_EXTS)
        ]
        if len(files) == 0:
            print(f"  [WARN] No images in '{cls_folder}', skipping.")
            continue
        print(f"    {cls:20s}: {len(files)} images")
        for fname in files:
            fpath = os.path.join(cls_folder, fname)
            try:
                img = tf.keras.utils.load_img(fpath, target_size=image_size)
                images.append(tf.keras.utils.img_to_array(img))
                labels.append(idx)
            except Exception as e:
                print(f"  [WARN] Could not read '{fname}': {e}")

    if len(images) == 0:
        raise ValueError(f"\n[ERROR] No readable images found in '{path}'.\n")

    return np.array(images, dtype="float32"), np.array(labels, dtype="int32"), classes


def split_data(x, y, train_pct, val_pct):
    """Shuffle and split arrays into train / val / test."""
    assert train_pct + val_pct < 100, "train_pct + val_pct must be < 100"
    x = x.astype("float32") / 255.0
    y = np.array(y).flatten()
    idx = np.random.default_rng(42).permutation(len(x))
    x, y = x[idx], y[idx]
    n         = len(x)
    tr_end    = int(n * train_pct / 100)
    va_end    = int(n * (train_pct + val_pct) / 100)
    return (x[:tr_end],    y[:tr_end],
            x[tr_end:va_end], y[tr_end:va_end],
            x[va_end:],    y[va_end:])



#  LOAD DATA


print("\n── Loading data ──")

if DATASET == "mnist":
    (x_tr, y_tr), (x_te, y_te) = keras.datasets.mnist.load_data()
    x_tr = x_tr[..., np.newaxis]
    x_te = x_te[..., np.newaxis]
    x_all = np.concatenate([x_tr, x_te])
    y_all = np.concatenate([y_tr.flatten(), y_te.flatten()])
    INPUT_SHAPE = (28, 28, 1)
    NUM_CLASSES = 10
    x_train, y_train, x_val, y_val, x_test, y_test = split_data(
        x_all, y_all, TRAIN_PCT, VAL_PCT)

elif DATASET == "fashion_mnist":
    (x_tr, y_tr), (x_te, y_te) = keras.datasets.fashion_mnist.load_data()
    x_tr = x_tr[..., np.newaxis]
    x_te = x_te[..., np.newaxis]
    x_all = np.concatenate([x_tr, x_te])
    y_all = np.concatenate([y_tr.flatten(), y_te.flatten()])
    INPUT_SHAPE = (28, 28, 1)
    NUM_CLASSES = 10
    x_train, y_train, x_val, y_val, x_test, y_test = split_data(
        x_all, y_all, TRAIN_PCT, VAL_PCT)

elif DATASET == "cifar10":
    (x_tr, y_tr), (x_te, y_te) = keras.datasets.cifar10.load_data()
    x_all = np.concatenate([x_tr, x_te])
    y_all = np.concatenate([y_tr.flatten(), y_te.flatten()])
    INPUT_SHAPE = (32, 32, 3)
    NUM_CLASSES = 10
    x_train, y_train, x_val, y_val, x_test, y_test = split_data(
        x_all, y_all, TRAIN_PCT, VAL_PCT)

elif DATASET == "cifar100":
    (x_tr, y_tr), (x_te, y_te) = keras.datasets.cifar100.load_data()
    x_all = np.concatenate([x_tr, x_te])
    y_all = np.concatenate([y_tr.flatten(), y_te.flatten()])
    INPUT_SHAPE = (32, 32, 3)
    NUM_CLASSES = 100
    x_train, y_train, x_val, y_val, x_test, y_test = split_data(
        x_all, y_all, TRAIN_PCT, VAL_PCT)

elif DATASET == "folder_split":
    # Folders already separated into train / val / test
    x_train, y_train, classes = load_folder(TRAIN_PATH, IMAGE_SIZE)
    x_val,   y_val,   _       = load_folder(VAL_PATH,   IMAGE_SIZE, classes)
    x_test,  y_test,  _       = load_folder(TEST_PATH,  IMAGE_SIZE, classes)
    NUM_CLASSES = len(classes)
    INPUT_SHAPE = (IMAGE_SIZE[0], IMAGE_SIZE[1], 3)
    # Normalise
    x_train = x_train / 255.0
    x_val   = x_val   / 255.0
    x_test  = x_test  / 255.0
    y_train = y_train.flatten()
    y_val   = y_val.flatten()
    y_test  = y_test.flatten()

elif DATASET == "folder_auto":
    # Single folder — split automatically
    x_all, y_all, classes = load_folder(SINGLE_PATH, IMAGE_SIZE)
    NUM_CLASSES = len(classes)
    INPUT_SHAPE = (IMAGE_SIZE[0], IMAGE_SIZE[1], 3)
    x_train, y_train, x_val, y_val, x_test, y_test = split_data(
        x_all, y_all, TRAIN_PCT, VAL_PCT)

else:
    raise ValueError(
        f"Unknown DATASET='{DATASET}'.\n"
        f"Choose: mnist | fashion_mnist | cifar10 | cifar100 "
        f"| folder_split | folder_auto"
    )

print(f"\n  Train   : {len(x_train):,}")
print(f"  Val     : {len(x_val):,}")
print(f"  Test    : {len(x_test):,}")
print(f"  Classes : {NUM_CLASSES}")
print(f"  Shape   : {INPUT_SHAPE}")



#  MODEL


def dw_block(x, filters, stride=1):
    """Depthwise-separable block — cheap but effective."""
    x = layers.DepthwiseConv2D(3, strides=stride, padding="same", use_bias=False)(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU(6.0)(x)
    x = layers.Conv2D(filters, 1, use_bias=False)(x)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU(6.0)(x)
    return x


inputs = keras.Input(shape=INPUT_SHAPE)

# Augmentation (only active during training)
x = layers.RandomFlip("horizontal")(inputs)
x = layers.RandomRotation(0.1)(x)

# Stem
x = layers.Conv2D(16, 3, padding="same", use_bias=False)(x)
x = layers.BatchNormalization()(x)
x = layers.ReLU(6.0)(x)

# Body
x = dw_block(x, 32, stride=2)
x = dw_block(x, 64, stride=2)
x = dw_block(x, 64, stride=2)

# Head
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.2)(x)
outputs = layers.Dense(NUM_CLASSES, activation="softmax")(x)

model = keras.Model(inputs, outputs, name="ExamModel")
model.summary()
print(f"\nTotal parameters: {model.count_params():,}")

#  TRAIN


model.compile(
    optimizer=keras.optimizers.Adam(0.001),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"],
)

history = model.fit(
    x_train, y_train,
    epochs=EPOCHS,
    batch_size=BATCH_SIZE,
    validation_data=(x_val, y_val),
    callbacks=[
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_accuracy", factor=0.5,
            patience=5, min_lr=1e-5, verbose=1),
        keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=10,
            restore_best_weights=True, verbose=1),
        keras.callbacks.ModelCheckpoint(
            SAVE_PATH, monitor="val_accuracy",
            save_best_only=True, verbose=1),
    ],
    verbose=1,
)

print(f"\nModel saved → {SAVE_PATH}")


#  SCORE


preds       = model.predict(x_test, batch_size=256, verbose=0)
y_pred      = np.argmax(preds, axis=1)
correct_raw = int(np.sum(y_pred == y_test))
scale       = 10000 / len(y_test)
correct     = int(correct_raw * scale)        # scaled to 10,000

tier1  = min(correct, 5000)                 * 100
tier2  = max(0, min(correct - 5000, 1000))  * 200
tier3  = max(0, correct - 6000)             * 1000
reward = tier1 + tier2 + tier3
params = model.count_params()
net    = reward - params

print("\n" + "="*52)
print("  EXAM SCORE")
print("="*52)
print(f"  Accuracy          : {correct_raw / len(y_test) * 100:.1f}%")
print(f"  Correct (scaled)  : {correct:,} / 10,000")
print(f"  Tier 1 reward     : {tier1:>14,} EUR")
print(f"  Tier 2 reward     : {tier2:>14,} EUR")
print(f"  Tier 3 reward     : {tier3:>14,} EUR")
print(f"  Gross reward      : {reward:>14,} EUR")
print(f"  Param penalty     : {params:>14,}")
print(f"  NET SCORE         : {net:>14,} EUR")
print("="*52)


#  PLOT

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
fig.suptitle(f"ExamModel — {DATASET}", fontsize=13)

axes[0].plot(history.history["accuracy"],     label="Train")
axes[0].plot(history.history["val_accuracy"], label="Val")
axes[0].set_title("Accuracy")
axes[0].set_xlabel("Epoch")
axes[0].legend()

axes[1].plot(history.history["loss"],         label="Train")
axes[1].plot(history.history["val_loss"],     label="Val")
axes[1].set_title("Loss")
axes[1].set_xlabel("Epoch")
axes[1].legend()

plt.tight_layout()
plt.savefig("training_history.png", dpi=150)
print("Plot saved → training_history.png")
