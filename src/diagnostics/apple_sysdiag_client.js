/*
 * APPLE SYSDIAGNOSE CLIENT-SIDE EXTRACTION ENGINE
 * Mufti Computer Vision - Pusat Gadai Indonesia
 *
 * Runs inside the browser on the iPhone being tested. The sysdiagnose
 * archive (.tar.gz, typically 300-400 MB) is streamed from local storage
 * through the native gzip decompressor and the tar headers are parsed on the
 * fly. Only the small telemetry files are kept (sysctl, BatteryHealth,
 * asptool snapshot, FDR report, crash file names). Reading stops as soon as
 * the crash section has been passed, so the large logarchive / powerlog
 * blobs at the end of the archive are never decompressed and nothing large
 * is ever uploaded. The resulting summary is only a few kilobytes.
 */
(function (global) {
    "use strict";

    var DEC = new TextDecoder("utf-8");
    var PAKO_URL = "https://cdn.jsdelivr.net/npm/pako@2.1.0/dist/pako.min.js";

    function readStr(buf, off, len) {
        var end = off, lim = off + len;
        while (end < lim && buf[end] !== 0) end++;
        return DEC.decode(buf.subarray(off, end));
    }

    function readSize(buf, off, len) {
        if (buf[off] & 0x80) {
            // GNU base-256 encoding for very large members
            var v = 0;
            for (var i = off + 1; i < off + len; i++) v = v * 256 + buf[i];
            return v;
        }
        var s = readStr(buf, off, len).trim();
        return s ? parseInt(s, 8) : 0;
    }

    function isZeroBlock(b) {
        for (var i = 0; i < b.length; i++) if (b[i] !== 0) return false;
        return true;
    }

    function ByteQueue() { this.chunks = []; this.len = 0; }
    ByteQueue.prototype.push = function (c) {
        if (c && c.length) { this.chunks.push(c); this.len += c.length; }
    };
    ByteQueue.prototype.take = function (n) {
        var out = new Uint8Array(n), o = 0;
        while (o < n) {
            var c = this.chunks[0], need = n - o;
            if (c.length <= need) { out.set(c, o); o += c.length; this.chunks.shift(); }
            else { out.set(c.subarray(0, need), o); this.chunks[0] = c.subarray(need); o += need; }
        }
        this.len -= n;
        return out;
    };
    ByteQueue.prototype.skip = function (n) {
        var s = 0;
        while (s < n && this.chunks.length) {
            var c = this.chunks[0], need = n - s;
            if (c.length <= need) { s += c.length; this.chunks.shift(); }
            else { this.chunks[0] = c.subarray(need); s += need; }
        }
        this.len -= s;
        return s;
    };

    function loadPako() {
        return new Promise(function (resolve, reject) {
            if (global.pako) return resolve(global.pako);
            var sc = document.createElement("script");
            sc.src = PAKO_URL;
            sc.onload = function () { global.pako ? resolve(global.pako) : reject(new Error("pako tidak tersedia")); };
            sc.onerror = function () { reject(new Error("Browser tidak mendukung dekompresi gzip dan pustaka cadangan gagal dimuat. Perbarui iOS ke versi 16.4 atau lebih baru.")); };
            document.head.appendChild(sc);
        });
    }

    function pakoStream(file, counter) {
        var offset = 0, CH = 1 << 20, inflator = null;
        return new ReadableStream({
            start: function (ctrl) {
                inflator = new global.pako.Inflate();
                inflator.onData = function (c) { ctrl.enqueue(c.slice()); };
            },
            pull: function (ctrl) {
                if (offset >= file.size) { ctrl.close(); return; }
                return file.slice(offset, offset + CH).arrayBuffer().then(function (ab) {
                    offset += CH;
                    counter.compressed = Math.min(offset, file.size);
                    inflator.push(new Uint8Array(ab), offset >= file.size);
                    if (inflator.err) ctrl.error(new Error(inflator.msg || "Gagal dekompresi"));
                    else if (offset >= file.size) ctrl.close();
                });
            }
        });
    }

    async function openDecompressedStream(file, counter, forcePako) {
        if (!forcePako && typeof DecompressionStream !== "undefined") {
            var counting = new TransformStream({
                transform: function (chunk, ctrl) { counter.compressed += chunk.length; ctrl.enqueue(chunk); }
            });
            return file.stream().pipeThrough(counting).pipeThrough(new DecompressionStream("gzip"));
        }
        await loadPako();
        return pakoStream(file, counter);
    }

    var ASP_KEYS = ["Grown Bad Blocks Count", "Factory Bad Blocks Count", "powerOnHours", "smartCritWarnings",
                    "numGrownBad", "averageTLCPECycles", "averageSLCPECycles", "slcPercentUsed", "maxSLCEndurance"];

    function summarizeAsptool(text) {
        var out = [], seen = {};
        var lines = text.split(/\r?\n/);
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            for (var k = 0; k < ASP_KEYS.length; k++) {
                var key = ASP_KEYS[k];
                if (!seen[key] && line.indexOf(key + ":") === 0) {
                    seen[key] = true;
                    out.push(line.replace(/\s+/g, " "));
                }
            }
        }
        return out.join("\n");
    }

    function maskMiddle(s, head, tail) {
        if (!s) return "";
        if (s.length < head + tail) return s;
        return s.slice(0, head) + "***" + s.slice(s.length - tail);
    }

    function parseFdrPlist(xml) {
        var props = {};
        var re = /<key>([^<]+)<\/key>\s*<dict>\s*<key>LiveProperty<\/key>\s*<string>([^<]*)<\/string>/g, m;
        while ((m = re.exec(xml)) !== null) {
            if (!(m[1] in props)) props[m[1]] = m[2];
        }
        var ap = /<key>ApTicket<\/key>\s*<string>([^<]*)<\/string>/.exec(xml);
        var seal = /<key>SealDate<\/key>\s*<(?:string|date)>([^<]*)<\/(?:string|date)>/.exec(xml);
        return {
            serial: maskMiddle(props["SrNm"] || "", 3, 3),
            imei: maskMiddle(props["imei"] || "", 3, 4),
            mlb: maskMiddle(props["mlb#"] || "", 4, 4),
            ap_ticket: ap ? ap[1] : "",
            seal_date: seal ? seal[1] : ""
        };
    }

    var JSON_KEYS = ["record", "deviceModel", "testSummary", "batteryTelemetry", "appleDiagnostics"];

    /**
     * Extracts Apple hardware telemetry from a sysdiagnose .tar.gz File object.
     * onProgress({entries, decompressedMB, compressedMB, elapsedMs}) is optional.
     */
    async function extractAppleTelemetry(file, onProgress, opts) {
        opts = opts || {};
        var t0 = performance.now();
        var counter = { compressed: 0 };
        var stream = await openDecompressedStream(file, counter, !!opts.forcePako);
        var reader = stream.getReader();
        var q = new ByteQueue();
        var finished = false, decompressed = 0;

        async function fill(n) {
            while (q.len < n && !finished) {
                var r = await reader.read();
                if (r.done) { finished = true; break; }
                q.push(r.value);
                decompressed += r.value.length;
            }
            return q.len >= n;
        }

        async function skipBytes(n) {
            while (n > 0) {
                if (q.len === 0 && !(await fill(1))) return false;
                n -= q.skip(n);
            }
            return true;
        }

        var res = {
            source: "client_js",
            engine: (!opts.forcePako && typeof DecompressionStream !== "undefined") ? "native" : "pako",
            filename: file.name, file_size: file.size, root: "",
            sysctl: "", battery: "", asptool: "", fdr: null,
            crashes: [], panic_files: [], panics: ""
        };

        var pendingName = null, idx = 0, sawCrash = false, leftCrash = false, lastReport = 0;

        while (true) {
            if (!(await fill(512))) break;
            var h = q.take(512);
            if (isZeroBlock(h)) break;

            var name = readStr(h, 0, 100);
            var size = readSize(h, 124, 12);
            var type = h[156] ? String.fromCharCode(h[156]) : "0";
            if (readStr(h, 257, 6).indexOf("ustar") === 0) {
                var prefix = readStr(h, 345, 155);
                if (prefix) name = prefix + "/" + name;
            }
            var padded = Math.ceil(size / 512) * 512;

            if (type === "x" || type === "L" || type === "g") {
                if (!(await fill(padded))) break;
                var meta = q.take(padded).subarray(0, size);
                if (type === "L") pendingName = readStr(meta, 0, size);
                else if (type === "x") {
                    var pm = /\d+ path=([^\n]*)\n/.exec(DEC.decode(meta));
                    if (pm) pendingName = pm[1];
                }
                continue;
            }
            if (pendingName) { name = pendingName; pendingName = null; }
            idx++;

            if (!res.root && name.indexOf("/") > 0) res.root = name.split("/")[0];
            var base = name.substring(name.lastIndexOf("/") + 1);
            var appleDouble = name.indexOf("._") !== -1 || base.indexOf("._") === 0;
            var isFile = (type === "0" || type === "7");

            var want = null;
            if (isFile && !appleDouble && size < 8 * 1024 * 1024) {
                if (/sysctl\.txt$/.test(name)) want = "sysctl";
                else if (name.indexOf("asptool_snapshot.log") !== -1) want = "asptool";
                else if (name.indexOf("logs/BatteryHealth/BatteryHealth.log") !== -1 ||
                         (/BatteryHealth\.log$/.test(name) && !res.battery)) want = "battery";
                else if (/FDRDiagnosticReport\.plist$/.test(name)) want = "fdr";
                else if (name.indexOf("Panics.log") !== -1 || name.indexOf("MCUPanicLogs.log") !== -1) want = "panics";
                else if (/\.json$/i.test(name) && /diagnostic|sysdiagnose/i.test(name)) want = "json";
            }

            var inCrash = name.indexOf("/crashes_and_spins/") !== -1;
            if (inCrash) sawCrash = true; else if (sawCrash) leftCrash = true;
            if (inCrash && isFile && !appleDouble && /\.ips$/i.test(base)) {
                if (res.crashes.length < 25) res.crashes.push(base);
                if (base.toLowerCase().indexOf("panic") !== -1) res.panic_files.push(base);
            }

            if (want) {
                if (!(await fill(padded))) break;
                var text = DEC.decode(q.take(padded).subarray(0, size));
                if (want === "asptool") res.asptool = summarizeAsptool(text);
                else if (want === "fdr") res.fdr = parseFdrPlist(text);
                else if (want === "panics") res.panics += text.slice(0, 4000);
                else if (want === "json") {
                    try {
                        var o = JSON.parse(text);
                        if (o && typeof o === "object" && JSON_KEYS.some(function (k) { return k in o; })) {
                            res.diagnostic_json = o;
                            break;
                        }
                    } catch (e) { /* not a diagnostic report */ }
                } else res[want] = text.slice(0, 20000);
            } else if (!(await skipBytes(padded))) break;

            var now = performance.now();
            if (onProgress && now - lastReport > 120) {
                lastReport = now;
                onProgress({ entries: idx, decompressedMB: decompressed / 1048576,
                             compressedMB: counter.compressed / 1048576, elapsedMs: now - t0 });
            }

            var hasCore = !!(res.battery && res.asptool && res.fdr);
            if (hasCore && (leftCrash || idx > 260)) break;
            if (idx > 400 && (res.battery || res.asptool)) break;
        }

        try { await reader.cancel(); } catch (e) { /* stream already closed */ }

        res.entries = idx;
        res.decompressed_mb = Math.round(decompressed / 104857.6) / 10;
        res.elapsed_ms = Math.round(performance.now() - t0);
        if (!res.diagnostic_json && !res.battery && !res.asptool && !res.fdr) {
            throw new Error("Berkas ini tidak berisi data sysdiagnose Apple yang dikenali.");
        }
        return res;
    }

    /** Quick values for the on-phone result card (server computes the final report). */
    function summarizeForDisplay(res) {
        var soh = null, poh = null, bad = null;
        var m = /"Maximum Capacity Percent"\s*=\s*(\d+)/.exec(res.battery || "");
        if (m) soh = parseInt(m[1], 10);
        m = /powerOnHours:\s*(\d+)/.exec(res.asptool || "");
        if (m) poh = parseInt(m[1], 10);
        m = /Grown Bad Blocks Count:\s*(\d+)/.exec(res.asptool || "");
        if (m) bad = parseInt(m[1], 10);
        var build = "";
        if (res.root && res.root.indexOf("iPhone-OS_iPhone_") !== -1) build = res.root.split("iPhone-OS_iPhone_").pop();
        return {
            soh: soh, poh: poh, grownBad: bad, build: build,
            crashCount: res.crashes.length,
            panic: res.panic_files.length > 0 || /panic\(cpu/i.test(res.panics || ""),
            serial: res.fdr ? res.fdr.serial : "", apTicket: res.fdr ? res.fdr.ap_ticket : ""
        };
    }

    global.AppleSysdiagClient = {
        extract: extractAppleTelemetry,
        summarize: summarizeForDisplay
    };
})(typeof window !== "undefined" ? window : this);
