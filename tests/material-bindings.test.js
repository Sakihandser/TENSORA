"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { applyMaterialBinding, normalizeMaterialPayload } = require("../server.js");

function library() {
  return normalizeMaterialPayload({
    materials: [{ id: "rock", name: "花岗岩", deformationMaterialId: "def-a", blastMaterialId: "blast-a" }],
    deformationMaterials: [
      { id: "def-a", name: "花岗岩-裂带", card: { model: "crackBand" } },
      { id: "def-b", name: "花岗岩-Mazars", card: { model: "mazars" } },
    ],
    blastMaterials: [],
  });
}

test("legacy single links become the active entry of the binding list", () => {
  const [rock] = library().materials;
  assert.deepEqual(rock.deformationMaterialIds, ["def-a"]);
  assert.deepEqual(rock.blastMaterialIds, ["blast-a"]);
});

test("a base material keeps several cards of one library and activates exactly one", () => {
  let payload = applyMaterialBinding(library(), { library: "deformation", materialId: "rock", cardId: "def-b", action: "bind" });
  let [rock] = payload.materials;
  assert.deepEqual(rock.deformationMaterialIds, ["def-a", "def-b"]);
  assert.equal(rock.deformationMaterialId, "def-a", "binding does not steal the active card");

  payload = applyMaterialBinding(payload, { library: "deformation", materialId: "rock", cardId: "def-b", action: "activate" });
  [rock] = payload.materials;
  assert.equal(rock.deformationMaterialId, "def-b");
  assert.deepEqual(rock.deformationMaterialIds, ["def-a", "def-b"]);

  payload = applyMaterialBinding(payload, { library: "deformation", materialId: "rock", cardId: "def-b", action: "unbind" });
  [rock] = payload.materials;
  assert.equal(rock.deformationMaterialId, null, "unbinding the active card leaves none active");
  assert.deepEqual(rock.deformationMaterialIds, ["def-a"]);

  payload = applyMaterialBinding(payload, { library: "deformation", materialId: "rock", cardId: "def-a", action: "activate" });
  payload = applyMaterialBinding(payload, { library: "deformation", materialId: "rock", cardId: "def-a", action: "deactivate" });
  [rock] = normalizeMaterialPayload(payload).materials;
  assert.equal(rock.deformationMaterialId, null);
  assert.deepEqual(rock.deformationMaterialIds, ["def-a"], "deactivating keeps the binding");
});

test("the first binding of an unbound material becomes active", () => {
  const start = applyMaterialBinding(library(), { library: "deformation", materialId: "rock", cardId: "def-a", action: "unbind" });
  const [rock] = applyMaterialBinding(start, { library: "deformation", materialId: "rock", cardId: "def-b", action: "bind" }).materials;
  assert.equal(rock.deformationMaterialId, "def-b");
});

test("unknown cards, materials and libraries are rejected", () => {
  assert.throws(() => applyMaterialBinding(library(), { library: "deformation", materialId: "rock", cardId: "missing", action: "bind" }), /找不到所选损伤变形材料卡/);
  assert.throws(() => applyMaterialBinding(library(), { library: "deformation", materialId: "nope", cardId: "def-a", action: "bind" }), /找不到所选基础材料/);
  assert.throws(() => applyMaterialBinding(library(), { library: "fluids", materialId: "rock", cardId: "def-a", action: "bind" }), /不支持的专业材料库/);
});
