/* fxtranslate 0.5.0 (MPL-2.0, https://www.npmjs.com/package/fxtranslate) wasm 바인딩 — Node 전용 부분만 브라우저용으로 고침(맨 아래). */
/* @ts-self-types="./fxtranslate_wasm.d.ts" */

/**
 * A translation engine callable from JavaScript.
 *
 * Owns its [`Engine`] (and, transitively, owned copies of the model bytes — the
 * engine borrows nothing from the `Uint8Array`s passed to the constructor), so
 * it stays valid across `translate` calls without the host holding the buffers.
 */
class Translator {
    __destroy_into_raw() {
        const ptr = this.__wbg_ptr;
        this.__wbg_ptr = 0;
        TranslatorFinalization.unregister(this);
        return ptr;
    }
    free() {
        const ptr = this.__destroy_into_raw();
        wasm.__wbg_translator_free(ptr, 0);
    }
    /**
     * The active int8 GEMM backend, so a silent scalar build can't be mistaken
     * for a SIMD one. Reports `"wasm-simd128"` when the crate was built for
     * `wasm32` with `-C target-feature=+simd128` (the pure-Rust SIMD128 kernel is
     * then live), and `"scalar"` for a plain scalar wasm build.
     * @returns {string}
     */
    backend() {
        let deferred1_0;
        let deferred1_1;
        try {
            const ret = wasm.translator_backend(this.__wbg_ptr);
            deferred1_0 = ret[0];
            deferred1_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred1_0, deferred1_1, 1);
        }
    }
    /**
     * Current wasm linear-memory size in bytes (pages x 64 KiB). Polled by the
     * perf harness after each block to report the linear-memory high-water mark —
     * mostly the ~150 MB owned model buffer plus activations. This is a *different*
     * metric from native settled/peak RSS (no shared file-backed pages, no mmap),
     * so the writeup compares them with that caveat, not as identical.
     * @returns {number}
     */
    linearMemoryBytes() {
        const ret = wasm.translator_linearMemoryBytes(this.__wbg_ptr);
        return ret;
    }
    /**
     * Build a translator from model + vocabulary bytes, with an optional lexical
     * shortlist.
     *
     * Pass byte-identical `src_vocab` and `trg_vocab` for shared-vocab pairs
     * (most pairs, including en→fr) and distinct buffers for split-vocab (CJK).
     * `shortlist` may be `null`/`undefined`; when present it restricts the output
     * vocabulary per sentence (required for exact reference parity).
     * @param {Uint8Array} model
     * @param {Uint8Array} src_vocab
     * @param {Uint8Array} trg_vocab
     * @param {Uint8Array | null} [shortlist]
     */
    constructor(model, src_vocab, trg_vocab, shortlist) {
        const ptr0 = passArray8ToWasm0(model, wasm.__wbindgen_malloc);
        const len0 = WASM_VECTOR_LEN;
        const ptr1 = passArray8ToWasm0(src_vocab, wasm.__wbindgen_malloc);
        const len1 = WASM_VECTOR_LEN;
        const ptr2 = passArray8ToWasm0(trg_vocab, wasm.__wbindgen_malloc);
        const len2 = WASM_VECTOR_LEN;
        var ptr3 = isLikeNone(shortlist) ? 0 : passArray8ToWasm0(shortlist, wasm.__wbindgen_malloc);
        var len3 = WASM_VECTOR_LEN;
        const ret = wasm.translator_new(ptr0, len0, ptr1, len1, ptr2, len2, ptr3, len3);
        if (ret[2]) {
            throw takeFromExternrefTable0(ret[1]);
        }
        this.__wbg_ptr = ret[0];
        TranslatorFinalization.register(this, this.__wbg_ptr, this);
        return this;
    }
    /**
     * Translate a single sentence-unit `text` and return the target text.
     * @param {string} text
     * @returns {string}
     */
    translate(text) {
        let deferred2_0;
        let deferred2_1;
        try {
            const ptr0 = passStringToWasm0(text, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len0 = WASM_VECTOR_LEN;
            const ret = wasm.translator_translate(this.__wbg_ptr, ptr0, len0);
            deferred2_0 = ret[0];
            deferred2_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred2_0, deferred2_1, 1);
        }
    }
    /**
     * Translate one block (its sentences, one per line in `block`) and report
     * per-phase boundaries to the host so it can time each phase itself.
     *
     * wasm has no usable `std::time::Instant` (it panics on
     * `wasm32-unknown-unknown`), so the native `--timing` spans don't work here.
     * Instead the host passes `on_phase`, a JS function the engine calls at the
     * encode/decode/first-token boundaries; the host records `performance.now()`
     * on each call and derives TTFT + decode tok/s the same way `perf.py` does
     * from the native `Instant` spans. `on_phase` receives the phase name as a
     * string: `"encode_start"`, `"decode_start"`, `"first_token"`, `"decode_end"`.
     *
     * Returns the block translation (sentences rejoined with `\n`) followed by a
     * trailing line of the shape `sentences\tsrc_tokens\ttokens` so the host has
     * the counts (words are host-counted from the source) without a second call.
     * @param {string} block
     * @param {Function} on_phase
     * @returns {string}
     */
    translateBlockPhased(block, on_phase) {
        let deferred2_0;
        let deferred2_1;
        try {
            const ptr0 = passStringToWasm0(block, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len0 = WASM_VECTOR_LEN;
            const ret = wasm.translator_translateBlockPhased(this.__wbg_ptr, ptr0, len0, on_phase);
            deferred2_0 = ret[0];
            deferred2_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred2_0, deferred2_1, 1);
        }
    }
    /**
     * Translate `text` of arbitrary length: split into sentences with ICU4X
     * (UAX #29, the same engine the native CLI uses) and translate each within
     * the model's context window, rejoined with the original whitespace.
     * @param {string} text
     * @returns {string}
     */
    translate_long(text) {
        let deferred2_0;
        let deferred2_1;
        try {
            const ptr0 = passStringToWasm0(text, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len0 = WASM_VECTOR_LEN;
            const ret = wasm.translator_translate_long(this.__wbg_ptr, ptr0, len0);
            deferred2_0 = ret[0];
            deferred2_1 = ret[1];
            return getStringFromWasm0(ret[0], ret[1]);
        } finally {
            wasm.__wbindgen_free(deferred2_0, deferred2_1, 1);
        }
    }
}
if (Symbol.dispose) Translator.prototype[Symbol.dispose] = Translator.prototype.free;

/**
 * Classify every language reachable through `hub` (e.g. `"en"`) by the
 * directions it supports, from a Remote Settings `records` body — the data the
 * `list` command renders.
 *
 * Takes the raw collection JSON. Returns
 * `{"bidirectional":[..],"sourceOnly":[..],"targetOnly":[..]}`, each a sorted
 * language-tag array. Throws only on a JSON parse error.
 * @param {string} records_json
 * @param {string} hub
 * @returns {string}
 */
function catalog(records_json, hub) {
    let deferred4_0;
    let deferred4_1;
    try {
        const ptr0 = passStringToWasm0(records_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ptr1 = passStringToWasm0(hub, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len1 = WASM_VECTOR_LEN;
        const ret = wasm.catalog(ptr0, len0, ptr1, len1);
        var ptr3 = ret[0];
        var len3 = ret[1];
        if (ret[3]) {
            ptr3 = 0; len3 = 0;
            throw takeFromExternrefTable0(ret[2]);
        }
        deferred4_0 = ptr3;
        deferred4_1 = len3;
        return getStringFromWasm0(ptr3, len3);
    } finally {
        wasm.__wbindgen_free(deferred4_0, deferred4_1, 1);
    }
}

/**
 * The unique, version-gated `src → trg` model pairs from a Remote Settings
 * `records` body — the raw one-way models the `list --all` view enumerates.
 *
 * Takes the raw collection JSON. Returns a JSON array of `[src, trg]` pairs,
 * already sorted and deduplicated and filtered to the supported model major —
 * so the JS shell renders exactly what `translate` could load without
 * reimplementing the version gate. The shell does its own prefix filtering on
 * this list (a shallow, safe-to-duplicate concern). Throws on a JSON parse error.
 * @param {string} records_json
 * @returns {string}
 */
function modelPairs(records_json) {
    let deferred3_0;
    let deferred3_1;
    try {
        const ptr0 = passStringToWasm0(records_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.modelPairs(ptr0, len0);
        var ptr2 = ret[0];
        var len2 = ret[1];
        if (ret[3]) {
            ptr2 = 0; len2 = 0;
            throw takeFromExternrefTable0(ret[2]);
        }
        deferred3_0 = ptr2;
        deferred3_1 = len2;
        return getStringFromWasm0(ptr2, len2);
    } finally {
        wasm.__wbindgen_free(deferred3_0, deferred3_1, 1);
    }
}

/**
 * Parse a Remote Settings `records` response body into the model-file records
 * fxtranslate understands, returned as a JSON array.
 *
 * The host fetches the collection JSON itself (async `fetch`) and passes the
 * body in; this normalizes it to the fields routing needs (name, fileType,
 * languages, version, architecture, decompressedHash, location), skipping
 * records that lack the required fields — same rule as the native parser.
 * Returns the JSON array on success, or throws with the parse error.
 * @param {string} body
 * @returns {string}
 */
function parseRecords(body) {
    let deferred3_0;
    let deferred3_1;
    try {
        const ptr0 = passStringToWasm0(body, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.parseRecords(ptr0, len0);
        var ptr2 = ret[0];
        var len2 = ret[1];
        if (ret[3]) {
            ptr2 = 0; len2 = 0;
            throw takeFromExternrefTable0(ret[2]);
        }
        deferred3_0 = ptr2;
        deferred3_1 = len2;
        return getStringFromWasm0(ptr2, len2);
    } finally {
        wasm.__wbindgen_free(deferred3_0, deferred3_1, 1);
    }
}

/**
 * Resolve `src`→`trg` against a Remote Settings `records` body to the route
 * that realizes it: a direct model, or a two-leg pivot through a hub.
 *
 * Takes the raw collection JSON (the same body [`parseRecords`] accepts) so the
 * host doesn't have to round-trip a records representation back across the
 * boundary. Returns one of
 * `{"kind":"direct","src":..,"trg":..}` or
 * `{"kind":"pivot","src":..,"pivot":..,"trg":..}`,
 * or throws when neither a direct model nor a pivot exists.
 * @param {string} records_json
 * @param {string} src
 * @param {string} trg
 * @returns {string}
 */
function resolveRoute(records_json, src, trg) {
    let deferred5_0;
    let deferred5_1;
    try {
        const ptr0 = passStringToWasm0(records_json, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ptr1 = passStringToWasm0(src, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len1 = WASM_VECTOR_LEN;
        const ptr2 = passStringToWasm0(trg, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len2 = WASM_VECTOR_LEN;
        const ret = wasm.resolveRoute(ptr0, len0, ptr1, len1, ptr2, len2);
        var ptr4 = ret[0];
        var len4 = ret[1];
        if (ret[3]) {
            ptr4 = 0; len4 = 0;
            throw takeFromExternrefTable0(ret[2]);
        }
        deferred5_0 = ptr4;
        deferred5_1 = len4;
        return getStringFromWasm0(ptr4, len4);
    } finally {
        wasm.__wbindgen_free(deferred5_0, deferred5_1, 1);
    }
}

/**
 * Split `text` into sentence units with ICU4X (UAX #29) and return their
 * trimmed content as a JSON string array.
 *
 * This is the same [`IcuSegmenter`] the wasm `Translator.translate_long`
 * drives, exposed so the JS shell can segment before batching and get the
 * exact boundaries the translate path will use. Whitespace between sentences
 * is not preserved here (the CLI reassembles from the source with
 * `reassemble`); this yields the sentence contents in order.
 * @param {string} text
 * @returns {string}
 */
function segmentSentences(text) {
    let deferred2_0;
    let deferred2_1;
    try {
        const ptr0 = passStringToWasm0(text, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
        const len0 = WASM_VECTOR_LEN;
        const ret = wasm.segmentSentences(ptr0, len0);
        deferred2_0 = ret[0];
        deferred2_1 = ret[1];
        return getStringFromWasm0(ret[0], ret[1]);
    } finally {
        wasm.__wbindgen_free(deferred2_0, deferred2_1, 1);
    }
}

/**
 * Decompress a zstd model attachment and verify the decompressed bytes against
 * an expected hex SHA-256 (a record's `decompressedHash`), returning the
 * decompressed bytes.
 *
 * The JS shell downloads the `.zst` attachment itself and calls this to decode
 * + verify before writing it to its cache — so it never reimplements zstd or
 * SHA-256. Pass `expected_sha256_hex` = `null`/`undefined` to decompress
 * without verifying (records that carry no hash). Throws on a decode failure or
 * a hash mismatch.
 * @param {Uint8Array} compressed
 * @param {string | null} [expected_sha256_hex]
 * @returns {Uint8Array}
 */
function verifyAndDecompress(compressed, expected_sha256_hex) {
    const ptr0 = passArray8ToWasm0(compressed, wasm.__wbindgen_malloc);
    const len0 = WASM_VECTOR_LEN;
    var ptr1 = isLikeNone(expected_sha256_hex) ? 0 : passStringToWasm0(expected_sha256_hex, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
    var len1 = WASM_VECTOR_LEN;
    const ret = wasm.verifyAndDecompress(ptr0, len0, ptr1, len1);
    if (ret[3]) {
        throw takeFromExternrefTable0(ret[2]);
    }
    var v3 = getArrayU8FromWasm0(ret[0], ret[1]).slice();
    wasm.__wbindgen_free(ret[0], ret[1] * 1, 1);
    return v3;
}
function __wbg_get_imports() {
    const import0 = {
        __proto__: null,
        __wbg_Error_92b29b0548f8b746: function(arg0, arg1) {
            const ret = Error(getStringFromWasm0(arg0, arg1));
            return ret;
        },
        __wbg___wbindgen_throw_344f42d3211c4765: function(arg0, arg1) {
            throw new Error(getStringFromWasm0(arg0, arg1));
        },
        __wbg_call_a6e5c5dce5018821: function() { return handleError(function (arg0, arg1, arg2) {
            const ret = arg0.call(arg1, arg2);
            return ret;
        }, arguments); },
        __wbg_error_a6fa202b58aa1cd3: function(arg0, arg1) {
            let deferred0_0;
            let deferred0_1;
            try {
                deferred0_0 = arg0;
                deferred0_1 = arg1;
                console.error(getStringFromWasm0(arg0, arg1));
            } finally {
                wasm.__wbindgen_free(deferred0_0, deferred0_1, 1);
            }
        },
        __wbg_new_227d7c05414eb861: function() {
            const ret = new Error();
            return ret;
        },
        __wbg_stack_3b0d974bbf31e44f: function(arg0, arg1) {
            const ret = arg1.stack;
            const ptr1 = passStringToWasm0(ret, wasm.__wbindgen_malloc, wasm.__wbindgen_realloc);
            const len1 = WASM_VECTOR_LEN;
            getDataViewMemory0().setInt32(arg0 + 4 * 1, len1, true);
            getDataViewMemory0().setInt32(arg0 + 4 * 0, ptr1, true);
        },
        __wbindgen_cast_0000000000000001: function(arg0, arg1) {
            // Cast intrinsic for `Ref(String) -> Externref`.
            const ret = getStringFromWasm0(arg0, arg1);
            return ret;
        },
        __wbindgen_init_externref_table: function() {
            const table = wasm.__wbindgen_externrefs;
            const offset = table.grow(4);
            table.set(0, undefined);
            table.set(offset + 0, undefined);
            table.set(offset + 1, null);
            table.set(offset + 2, true);
            table.set(offset + 3, false);
        },
    };
    return {
        __proto__: null,
        "./fxtranslate_wasm_bg.js": import0,
    };
}

const TranslatorFinalization = (typeof FinalizationRegistry === 'undefined')
    ? { register: () => {}, unregister: () => {} }
    : new FinalizationRegistry(ptr => wasm.__wbg_translator_free(ptr, 1));

function addToExternrefTable0(obj) {
    const idx = wasm.__externref_table_alloc();
    wasm.__wbindgen_externrefs.set(idx, obj);
    return idx;
}

function getArrayU8FromWasm0(ptr, len) {
    ptr = ptr >>> 0;
    return getUint8ArrayMemory0().subarray(ptr / 1, ptr / 1 + len);
}

let cachedDataViewMemory0 = null;
function getDataViewMemory0() {
    if (cachedDataViewMemory0 === null || cachedDataViewMemory0.buffer.detached === true || (cachedDataViewMemory0.buffer.detached === undefined && cachedDataViewMemory0.buffer !== wasm.memory.buffer)) {
        cachedDataViewMemory0 = new DataView(wasm.memory.buffer);
    }
    return cachedDataViewMemory0;
}

function getStringFromWasm0(ptr, len) {
    return decodeText(ptr >>> 0, len);
}

let cachedUint8ArrayMemory0 = null;
function getUint8ArrayMemory0() {
    if (cachedUint8ArrayMemory0 === null || cachedUint8ArrayMemory0.byteLength === 0) {
        cachedUint8ArrayMemory0 = new Uint8Array(wasm.memory.buffer);
    }
    return cachedUint8ArrayMemory0;
}

function handleError(f, args) {
    try {
        return f.apply(this, args);
    } catch (e) {
        const idx = addToExternrefTable0(e);
        wasm.__wbindgen_exn_store(idx);
    }
}

function isLikeNone(x) {
    return x === undefined || x === null;
}

function passArray8ToWasm0(arg, malloc) {
    const ptr = malloc(arg.length * 1, 1) >>> 0;
    getUint8ArrayMemory0().set(arg, ptr / 1);
    WASM_VECTOR_LEN = arg.length;
    return ptr;
}

function passStringToWasm0(arg, malloc, realloc) {
    if (realloc === undefined) {
        const buf = cachedTextEncoder.encode(arg);
        const ptr = malloc(buf.length, 1) >>> 0;
        getUint8ArrayMemory0().subarray(ptr, ptr + buf.length).set(buf);
        WASM_VECTOR_LEN = buf.length;
        return ptr;
    }

    let len = arg.length;
    let ptr = malloc(len, 1) >>> 0;

    const mem = getUint8ArrayMemory0();

    let offset = 0;

    for (; offset < len; offset++) {
        const code = arg.charCodeAt(offset);
        if (code > 0x7F) break;
        mem[ptr + offset] = code;
    }
    if (offset !== len) {
        if (offset !== 0) {
            arg = arg.slice(offset);
        }
        ptr = realloc(ptr, len, len = offset + arg.length * 3, 1) >>> 0;
        const view = getUint8ArrayMemory0().subarray(ptr + offset, ptr + len);
        const ret = cachedTextEncoder.encodeInto(arg, view);

        offset += ret.written;
        ptr = realloc(ptr, len, offset, 1) >>> 0;
    }

    WASM_VECTOR_LEN = offset;
    return ptr;
}

function takeFromExternrefTable0(idx) {
    const value = wasm.__wbindgen_externrefs.get(idx);
    wasm.__externref_table_dealloc(idx);
    return value;
}

let cachedTextDecoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });
cachedTextDecoder.decode();
function decodeText(ptr, len) {
    return cachedTextDecoder.decode(getUint8ArrayMemory0().subarray(ptr, ptr + len));
}

const cachedTextEncoder = new TextEncoder();

if (!('encodeInto' in cachedTextEncoder)) {
    cachedTextEncoder.encodeInto = function (arg, view) {
        const buf = cachedTextEncoder.encode(arg);
        view.set(buf);
        return {
            read: arg.length,
            written: buf.length
        };
    };
}

let WASM_VECTOR_LEN = 0;

// 브라우저(Web Worker)용으로 바꾼 부분 — 원본(Node)은 require('fs') 로 wasm 을 읽음. 대시보드 2026-11-08
let wasm;
async function fxInit(url) { const r = await fetch(url, { cache:'force-cache' }); if (!r.ok) throw new Error('wasm ' + r.status);
  const { instance } = await WebAssembly.instantiate(await r.arrayBuffer(), __wbg_get_imports()); wasm = instance.exports; wasm.__wbindgen_start(); return true; }
self.FxTranslate = { Translator, init:fxInit };
