const Tt = {
  icon: 28,
  sm: 64,
  md: 112,
  lg: 192,
  xl: 320
}, It = {
  connecting: { speed: 0.92, amplitude: 0.34, rings: 3, alpha: 0.7 },
  initializing: { speed: 0.82, amplitude: 0.3, rings: 3, alpha: 0.65 },
  listening: { speed: 0.48, amplitude: 0.18, rings: 2, alpha: 0.56 },
  thinking: { speed: 0.74, amplitude: 0.24, rings: 3, alpha: 0.62 },
  speaking: { speed: 1.18, amplitude: 0.42, rings: 4, alpha: 0.78 },
  idle: { speed: 0.28, amplitude: 0.1, rings: 2, alpha: 0.44 },
  disconnected: { speed: 0.2, amplitude: 0.08, rings: 1, alpha: 0.32 },
  failed: { speed: 0.24, amplitude: 0.08, rings: 1, alpha: 0.32 }
};
function Ut(e) {
  const P = e.match(/^#([0-9a-fA-F]{6})$/);
  if (!P) return [75, 143, 206];
  const N = P[1];
  return [
    Number.parseInt(N.slice(0, 2), 16),
    Number.parseInt(N.slice(2, 4), 16),
    Number.parseInt(N.slice(4, 6), 16)
  ];
}
function ft(e, P) {
  return Math.max(0, Math.min(255, Math.round(e + P)));
}
function Kt(e) {
  const { useEffect: P, useRef: N } = e;
  function O({
    size: X = "sm",
    state: Z = "thinking",
    color: D = "#4b8fce",
    colorShift: M = 0.28,
    className: $e,
    style: F
  }) {
    const _ = N(null), le = N(null), ne = Tt[X] ?? Tt.sm;
    return P(() => {
      const re = _.current, g = re == null ? void 0 : re.getContext("2d");
      if (!re || !g) return;
      const L = It[Z] ?? It.thinking, [z, B, Q] = Ut(D);
      let j = performance.now();
      const Ie = (b) => {
        const se = Math.max(1, Math.min(window.devicePixelRatio || 1, 2)), T = re.getBoundingClientRect(), Pe = Math.max(1, Math.floor(T.width * se)), me = Math.max(1, Math.floor(T.height * se));
        (re.width !== Pe || re.height !== me) && (re.width = Pe, re.height = me);
        const Ge = (b - j) / 1e3, xe = Pe / 2, ie = me / 2, oe = Math.min(Pe, me) * 0.28;
        g.clearRect(0, 0, Pe, me), g.globalCompositeOperation = "lighter";
        const _e = g.createRadialGradient(xe, ie, 0, xe, ie, oe * 2.2);
        _e.addColorStop(0, `rgba(${z}, ${B}, ${Q}, ${0.22 * L.alpha})`), _e.addColorStop(0.52, `rgba(${z}, ${B}, ${Q}, ${0.1 * L.alpha})`), _e.addColorStop(1, `rgba(${z}, ${B}, ${Q}, 0)`), g.fillStyle = _e, g.beginPath(), g.arc(xe, ie, oe * 2.1, 0, Math.PI * 2), g.fill();
        for (let be = 0; be < L.rings; be += 1) {
          const U = Ge * L.speed + be * 0.72, Je = Math.sin(U * 1.4) * M * 42, Ve = ft(z, Je), Fe = ft(B, -Je * 0.35), qe = ft(Q, Je * 0.2), at = 1 + Math.sin(U * 2.2) * L.amplitude * 0.6, Ue = 0.72 + Math.cos(U * 1.6) * L.amplitude * 0.28, Ze = (0.22 - be * 0.035) * L.alpha;
          g.save(), g.translate(xe, ie), g.rotate(U * 0.55), g.scale(at, Ue), g.strokeStyle = `rgba(${Ve}, ${Fe}, ${qe}, ${Ze})`, g.lineWidth = Math.max(1, ne * 0.035 - be * 0.25) * se, g.shadowColor = `rgba(${Ve}, ${Fe}, ${qe}, ${0.45 * L.alpha})`, g.shadowBlur = ne * 0.24 * se, g.beginPath();
          const Qe = 96;
          for (let Me = 0; Me <= Qe; Me += 1) {
            const Ne = Me / Qe * Math.PI * 2, lt = Math.sin(Ne * 3 + U * 2.4) * oe * L.amplitude * 0.16 + Math.cos(Ne * 5 - U) * oe * L.amplitude * 0.08, ce = oe + be * oe * 0.18 + lt, Re = Math.cos(Ne) * ce, et = Math.sin(Ne) * ce;
            Me === 0 ? g.moveTo(Re, et) : g.lineTo(Re, et);
          }
          g.closePath(), g.stroke(), g.restore();
        }
        g.globalCompositeOperation = "source-over";
        const Oe = g.createRadialGradient(xe, ie, 0, xe, ie, oe * 0.34);
        Oe.addColorStop(0, `rgba(248, 251, 255, ${0.38 * L.alpha})`), Oe.addColorStop(1, `rgba(${z}, ${B}, ${Q}, 0)`), g.fillStyle = Oe, g.beginPath(), g.arc(xe, ie, oe * 0.38, 0, Math.PI * 2), g.fill(), le.current = requestAnimationFrame(Ie);
      };
      return le.current = requestAnimationFrame((b) => {
        j = b, Ie(b);
      }), () => {
        le.current !== null && cancelAnimationFrame(le.current);
      };
    }, [D, M, ne, Z]), e.createElement("canvas", {
      ref: _,
      className: $e,
      "aria-hidden": !0,
      style: {
        width: ne,
        height: ne,
        display: "block",
        ...F
      }
    });
  }
  return O;
}
function Yt() {
  var St, bt, At, kt;
  const { React: e, antd: P, antdIcons: N, getApiUrl: O, getApiToken: X } = window.JotaDuo.host, {
    Card: Z,
    Table: D,
    Tag: M,
    Typography: $e,
    Space: F,
    Button: _,
    Input: le,
    Radio: ne,
    Collapse: re,
    Descriptions: g,
    Tooltip: L,
    Spin: z,
    message: B,
    theme: Q
  } = P, { Text: j } = $e, { TextArea: Ie } = le, { useState: b, useMemo: se, useCallback: T, useRef: Pe } = e, {
    InfoCircleOutlined: me,
    DownOutlined: Ge,
    RightOutlined: xe,
    CheckCircleOutlined: ie,
    FieldTimeOutlined: oe,
    FileTextOutlined: _e
  } = N || {};
  function Oe(t) {
    var i, d;
    const n = (d = (i = t == null ? void 0 : t.content) == null ? void 0 : i[0]) == null ? void 0 : d.data, o = n == null ? void 0 : n.arguments;
    if (typeof o == "string")
      try {
        return JSON.parse(o);
      } catch {
        return {};
      }
    return o ?? {};
  }
  function be() {
    return window.currentSessionId ?? null;
  }
  function U(t) {
    return typeof t == "string" ? t : t && typeof t == "object" && "text" in t ? t.text : String(t ?? "");
  }
  function Je(t) {
    if (t == null) return !0;
    const n = U(t).trim();
    return !!(!n || /^[¥$]?0+(\.0+)?$/.test(n) || /^[-–—]+$/.test(n));
  }
  async function Ve(t, n) {
    try {
      const o = X(), i = {
        "Content-Type": "application/json"
      };
      return o && (i.Authorization = `Bearer ${o}`), (await fetch(O("/interaction"), {
        method: "POST",
        headers: i,
        body: JSON.stringify({ session_id: t, result: n })
      })).ok;
    } catch {
      return !1;
    }
  }
  function Fe(t) {
    if (!t) return null;
    if (typeof t == "string")
      try {
        const n = JSON.parse(t);
        if (Array.isArray(n)) {
          const o = n.find(
            (i) => (i == null ? void 0 : i.type) === "text" && (i == null ? void 0 : i.text)
          );
          return (o == null ? void 0 : o.text) ?? null;
        }
        if (typeof n == "string") return n;
      } catch {
        return t;
      }
    if (Array.isArray(t)) {
      const n = t.find((o) => (o == null ? void 0 : o.type) === "text" && (o == null ? void 0 : o.text));
      return (n == null ? void 0 : n.text) ?? null;
    }
    return null;
  }
  function qe(t) {
    var a, c;
    if (!t || t.length < 2) return null;
    const n = (c = (a = t[1]) == null ? void 0 : a.data) == null ? void 0 : c.output, o = Fe(n);
    if (!o) return null;
    if (o.startsWith("Error:")) return o;
    const i = o.match(/^用户选择了「(.+?)」并确认部署$/);
    if (i) return `已确认部署「${i[1]}」`;
    const d = o.match(
      /^用户选择「(.+?)」并要求调整[：:](.+)$/
    );
    if (d)
      return `已选择「${d[1]}」并调整：${d[2]}`;
    if (o === "用户确认部署") return "已确认部署";
    const h = o.match(/^用户要求调整资源[：:](.+)$/);
    return h ? `已反馈调整意见：${h[1]}` : "已确认";
  }
  const ot = [
    "资源类型",
    "资源用途",
    "规格",
    "地域",
    "数量",
    "计费方式",
    "时长",
    "原价",
    "优惠",
    "预估算费用"
  ], at = new Set(
    ot.map((t) => t.toLowerCase())
  );
  function Ue(t) {
    if (!Array.isArray(t) || t.length !== 10) return !1;
    const n = U(t[0]).trim().toLowerCase();
    return at.has(n);
  }
  function Ze(t) {
    if (!Array.isArray(t) || t.length !== 10) return !1;
    const n = U(t[0]).trim();
    return /^(合计|总计|total)/i.test(n);
  }
  function Qe(t) {
    const n = [];
    let o = [];
    for (const i of t)
      o.push(i), Ze(i) && (n.push(o), o = []);
    return o.length > 0 && (n.length > 0 ? n[n.length - 1].push(...o) : n.push(o)), n.length > 0 ? n : [t];
  }
  function Me(t) {
    return typeof t == "string" ? t : t && typeof t == "object" && t.text ? t.url ? e.createElement(
      "a",
      {
        href: t.url,
        target: "_blank",
        rel: "noopener noreferrer"
      },
      t.text
    ) : t.text : String(t ?? "");
  }
  function Ne({ data: t }) {
    var Ce, f, v;
    const [n, o] = b("confirm"), [i, d] = b(""), [h, a] = b(!1), [c, l] = b(null), [R, k] = b(
      {}
    ), $ = e.useRef(!1), ee = e.useRef(null), [, ge] = b(0), G = t == null ? void 0 : t.content, V = G && G.length >= 2 && ((f = (Ce = G[1]) == null ? void 0 : Ce.data) == null ? void 0 : f.output), q = se(
      () => qe(G),
      [G]
    ), H = $.current || V || q !== null, u = se(() => {
      const x = Oe(t), s = x == null ? void 0 : x.data;
      if (!s) return null;
      try {
        const y = typeof s == "string" ? JSON.parse(s) : s;
        let m;
        if (x.strategy_names)
          try {
            const J = typeof x.strategy_names == "string" ? JSON.parse(x.strategy_names) : x.strategy_names;
            m = Array.isArray(J) ? J : [];
          } catch {
            m = [];
          }
        else y != null && y.proposal_names ? m = y.proposal_names : m = [];
        const A = m.length >= 2 ? m.length : 0;
        let C;
        if (Array.isArray(y) && y.length > 0)
          if (Array.isArray(y[0]) && y[0].length === 10 && !Array.isArray(y[0][0])) {
            const Y = y.filter(
              (Ee) => !Ue(Ee)
            );
            if (Y.filter(
              (Ee) => Ze(Ee)
            ).length >= 2)
              C = Qe(Y);
            else if (A >= 2 && Y.length >= A * 2) {
              const Ee = Math.ceil(Y.length / A);
              C = [];
              for (let Te = 0; Te < Y.length; Te += Ee)
                C.push(Y.slice(Te, Te + Ee));
            } else
              C = [Y];
          } else
            C = y.map(
              (Y) => Y.filter(
                (pe) => Array.isArray(pe) && pe.length === 10 && !Ue(pe)
              )
            );
        else if (y != null && y.proposals)
          C = y.proposals.map(
            (J) => J.filter((Y) => !Ue(Y))
          );
        else
          return null;
        if (C = C.filter((J) => J.length > 0), C.length === 0) return null;
        const we = ["方案一", "方案二", "方案三", "方案四", "方案五"];
        if (m.length < C.length)
          for (let J = m.length; J < C.length; J++)
            m.push(we[J] || `方案${J + 1}`);
        return { proposals: C, names: m };
      } catch {
        return null;
      }
    }, [t]), w = be(), p = (((v = u == null ? void 0 : u.proposals) == null ? void 0 : v.length) ?? 0) > 1, W = T(async () => {
      if (!w || H || !u) return;
      const x = p ? c : 0, s = u.names[x ?? 0] || `方案${(x ?? 0) + 1}`;
      let y;
      n === "confirm" ? y = `用户选择了「${s}」并确认部署` : y = `用户选择「${s}」并要求调整：${i.trim() || "未填写具体要求"}`, a(!0);
      const m = await Ve(w, y);
      a(!1), m ? ($.current = !0, n === "confirm" ? ee.current = `已确认部署「${s}」` : ee.current = `已选择「${s}」并调整：${i.trim()}`, ge((A) => A + 1), B.success(
        n === "confirm" ? "已确认部署方案" : "已提交调整意见"
      )) : B.error("操作失败，请重试");
    }, [
      w,
      H,
      u,
      n,
      i,
      c,
      p
    ]), Be = (t == null ? void 0 : t.status) === "in_progress" || (t == null ? void 0 : t.status) === "created";
    if (!u)
      return Be ? e.createElement(
        "div",
        {
          style: {
            width: "100%",
            borderRadius: 10,
            border: "1px solid #f0f0f0",
            background: "#fff",
            padding: "24px 16px",
            margin: "4px 0",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 12
          }
        },
        e.createElement(z, { size: "default" }),
        e.createElement(
          j,
          { type: "secondary", style: { fontSize: 13 } },
          "正在生成资源方案..."
        )
      ) : e.createElement(
        Z,
        { size: "small", style: { margin: "4px 0" } },
        e.createElement(j, { type: "secondary" }, "无法解析方案数据")
      );
    const { proposals: ue, names: Ae } = u, te = ot.map((x, s) => ({
      title: x,
      dataIndex: `col_${s}`,
      key: `col_${s}`,
      render: (y) => Me(y),
      ellipsis: s < 3
    }));
    let ke = "待确认", de = "processing";
    H && (de = "success", ke = ee.current || q || "已确认");
    const he = e.createElement(
      M,
      {
        color: de,
        style: { marginLeft: 4 }
      },
      ke
    ), je = e.createElement(
      F,
      { size: 8 },
      e.createElement("span", null, "☁️"),
      e.createElement(
        j,
        { strong: !0, style: { fontSize: 14 } },
        H ? "资源配置方案" : "请确认您的资源配置方案"
      ),
      he
    ), ve = ue.map((x, s) => {
      const y = p ? c === s : !0, m = R[s] || !1, A = (I) => {
        const fe = U(I[0] || "").trim();
        return /^合计|^总计|^total/i.test(fe);
      }, C = x.find(A), we = x.filter((I) => !A(I)), J = we.map((I) => ({
        type: U(I[0] || ""),
        purpose: U(I[1] || ""),
        spec: U(I[2] || ""),
        cost: I[9] ?? null
      })), Y = C ? U(C[9] ?? "") : "", pe = x.map((I, fe) => {
        const rt = { key: fe };
        return I.forEach((Ye, dt) => {
          rt[`col_${dt}`] = Ye;
        }), rt;
      }), Ee = y ? "2px solid #1677ff" : "1px solid #e8e8e8", Te = y ? "0 0 0 2px #e6f4ff" : "none";
      return e.createElement(
        "div",
        {
          key: s,
          style: {
            flex: 1,
            minWidth: 240,
            border: Ee,
            borderRadius: 8,
            cursor: p ? "pointer" : "default",
            transition: "all 0.2s ease",
            boxShadow: Te,
            background: "#fff"
          },
          onClick: p ? () => l(s) : void 0
        },
        e.createElement(
          "div",
          { style: { padding: "10px 12px" } },
          // Proposal name
          e.createElement(
            j,
            {
              strong: !0,
              style: { fontSize: 14, display: "block", marginBottom: 8 }
            },
            Ae[s]
          ),
          ...J.map(
            (I, fe) => e.createElement(
              "div",
              {
                key: fe,
                style: {
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "4px 0",
                  borderBottom: fe < J.length - 1 ? "1px solid #f5f5f5" : "none"
                }
              },
              e.createElement(
                "div",
                { style: { flex: 1, minWidth: 0 } },
                e.createElement(
                  "span",
                  { style: { fontSize: 12, color: "#262626" } },
                  I.type
                ),
                I.spec && e.createElement(
                  "span",
                  {
                    style: { fontSize: 11, color: "#8c8c8c", marginLeft: 6 }
                  },
                  I.spec
                )
              ),
              !Je(I.cost) && e.createElement(
                "span",
                {
                  style: {
                    fontSize: 12,
                    color: "#595959",
                    flexShrink: 0,
                    marginLeft: 8
                  }
                },
                U(I.cost)
              )
            )
          ),
          // Total cost
          Y && e.createElement(
            "div",
            {
              style: {
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginTop: 6,
                paddingTop: 6,
                borderTop: "1px dashed #e8e8e8"
              }
            },
            e.createElement(
              "span",
              { style: { fontSize: 12, fontWeight: 500 } },
              "合计"
            ),
            e.createElement(
              "span",
              {
                style: { fontSize: 14, fontWeight: 700, color: "#fa541c" }
              },
              Y
            )
          ),
          // Details toggle
          e.createElement(
            "div",
            {
              style: {
                display: "flex",
                alignItems: "center",
                gap: 4,
                color: "#8c8c8c",
                fontSize: 12,
                cursor: "pointer",
                marginTop: 6
              },
              onClick: (I) => {
                I.stopPropagation(), k((fe) => ({
                  ...fe,
                  [s]: !fe[s]
                }));
              }
            },
            e.createElement(
              m && Ge ? Ge : xe || "span",
              {
                style: { fontSize: 10 }
              }
            ),
            e.createElement(
              "span",
              null,
              `明细 · ${we.length} 项`
            )
          ),
          m && e.createElement(
            "div",
            {
              onClick: (I) => I.stopPropagation(),
              style: { marginTop: 4, maxHeight: 260, overflow: "auto" }
            },
            e.createElement(D, {
              columns: te,
              dataSource: pe,
              pagination: !1,
              size: "small",
              scroll: { x: "max-content" }
            })
          )
        )
      );
    }), ye = e.createElement(
      "div",
      {
        style: {
          background: "#fffbe6",
          border: "1px solid #ffe58f",
          borderRadius: 6,
          padding: "8px 12px",
          marginBottom: 10,
          display: "flex",
          alignItems: "flex-start",
          gap: 8
        }
      },
      me ? e.createElement(me, {
        style: {
          color: "#faad14",
          fontSize: 14,
          flexShrink: 0,
          marginTop: 1
        }
      }) : e.createElement("span", null, "⚠️"),
      e.createElement(
        "span",
        {
          style: { fontSize: 12, color: "#8c6e00", lineHeight: 1.5 }
        },
        "在服务部署与配置过程中，可能因实际资源需求变化导致资源变配及费用调整，请及时关注实际资源使用情况与账单详情。"
      )
    ), ze = !H && w && !(p && c === null) && e.createElement(
      "div",
      null,
      e.createElement(
        "div",
        {
          style: {
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            marginBottom: 8
          }
        },
        // Confirm option
        e.createElement(
          "div",
          {
            style: {
              flex: 1,
              minWidth: 140,
              border: `1px solid ${n === "confirm" ? "#1677ff" : "#e8e8e8"}`,
              borderRadius: 6,
              padding: "8px 12px",
              cursor: "pointer",
              transition: "all 0.15s ease",
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: n === "confirm" ? "#e6f4ff" : "transparent"
            },
            onClick: () => o("confirm")
          },
          e.createElement(ne, { checked: n === "confirm" }),
          e.createElement(
            "span",
            { style: { fontSize: 13 } },
            "确认部署"
          )
        ),
        // Adjust option
        e.createElement(
          "div",
          {
            style: {
              flex: 1,
              minWidth: 140,
              border: `1px solid ${n === "adjust" ? "#1677ff" : "#e8e8e8"}`,
              borderRadius: 6,
              padding: "8px 12px",
              transition: "all 0.15s ease",
              background: n === "adjust" ? "#e6f4ff" : "transparent"
            }
          },
          e.createElement(
            "div",
            {
              style: {
                display: "flex",
                alignItems: "center",
                gap: 8,
                cursor: "pointer"
              },
              onClick: () => o("adjust")
            },
            e.createElement(ne, { checked: n === "adjust" }),
            e.createElement(
              "span",
              { style: { fontSize: 13 } },
              "调整资源"
            )
          ),
          n === "adjust" && e.createElement(Ie, {
            value: i,
            onChange: (x) => d(x.target.value),
            placeholder: "请输入调整要求",
            autoSize: { minRows: 1, maxRows: 3 },
            style: { fontSize: 12, marginTop: 6 }
          })
        )
      ),
      // Footer
      e.createElement(
        "div",
        {
          style: {
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            paddingTop: 8
          }
        },
        e.createElement(
          j,
          { type: "secondary", style: { fontSize: 11 } },
          p ? "一小时后未操作将自动选择第一个方案" : "一小时后未操作将自动确认部署"
        ),
        e.createElement(
          _,
          {
            type: "primary",
            size: "small",
            loading: h,
            onClick: W,
            disabled: n === "adjust" && !i.trim()
          },
          n === "confirm" ? "确认部署" : "提交调整"
        )
      )
    ), K = p && c === null && !H && e.createElement(
      "div",
      {
        style: {
          textAlign: "center",
          padding: "8px 0 4px",
          color: "rgba(0,0,0,0.45)",
          fontSize: 12
        }
      },
      "请点击选择一个方案后继续操作"
    );
    return e.createElement(
      "div",
      {
        style: {
          width: "100%",
          borderRadius: 10,
          border: "1px solid #f0f0f0",
          overflow: "hidden",
          background: "#fff",
          padding: "12px 16px",
          margin: "4px 0"
        }
      },
      // Header
      e.createElement("div", { style: { marginBottom: 10 } }, je),
      // Proposals grid
      e.createElement(
        "div",
        {
          style: {
            display: "flex",
            gap: 10,
            marginBottom: 12,
            flexWrap: "wrap"
          }
        },
        ...ve
      ),
      K,
      ye,
      !H && ze
    );
  }
  function lt({ data: t }) {
    const [n, o] = b(null), [i, d] = b(!1), h = (t == null ? void 0 : t.status) === "in_progress" || (t == null ? void 0 : t.status) === "created", a = se(() => {
      const u = Oe(t);
      return (u == null ? void 0 : u.loop_dir) || null;
    }, [t]), c = se(() => {
      var w, p, W;
      const u = Fe((W = (p = (w = t == null ? void 0 : t.content) == null ? void 0 : w[1]) == null ? void 0 : p.data) == null ? void 0 : W.output);
      if (!u) return null;
      try {
        return JSON.parse(u);
      } catch {
        return null;
      }
    }, [t]), l = (c == null ? void 0 : c.status) === "ok", R = (c == null ? void 0 : c.status) === "error", k = R ? (c == null ? void 0 : c.message) || "未知错误" : null, $ = T(async () => {
      if (a)
        try {
          const u = X(), w = {};
          u && (w.Authorization = `Bearer ${u}`);
          const p = await fetch(
            O(`/prd?loop_dir=${encodeURIComponent(a)}`),
            { headers: w }
          );
          if (!p.ok) {
            d(!0);
            return;
          }
          const W = await p.json();
          W && Array.isArray(W.userStories) ? (o(W), d(!1)) : d(!0);
        } catch {
          d(!0);
        }
    }, [a]);
    if (e.useEffect(() => {
      !h && l && a && $();
    }, [h, l, a, $]), h)
      return e.createElement(
        "div",
        {
          style: {
            width: "100%",
            borderRadius: 10,
            border: "1px solid #f0f0f0",
            background: "#fff",
            padding: "24px 16px",
            margin: "4px 0",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 12
          }
        },
        e.createElement(z, { size: "default" }),
        e.createElement(
          j,
          { type: "secondary", style: { fontSize: 13 } },
          "正在更新 PRD..."
        )
      );
    if (R)
      return e.createElement(
        "div",
        {
          style: {
            width: "100%",
            borderRadius: 10,
            border: "1px solid #fff1f0",
            background: "#fff1f0",
            padding: "12px 16px",
            margin: "4px 0",
            display: "flex",
            alignItems: "center",
            gap: 8
          }
        },
        e.createElement(
          j,
          { type: "danger", style: { fontSize: 13 } },
          `PRD 格式错误，将会修正：${k}`
        )
      );
    if (!l || i || !n) return null;
    const ee = n.userStories, ge = [...ee].sort(
      (u, w) => (u.priority || 99) - (w.priority || 99)
    ), G = ee.filter((u) => u.passes).length, V = [
      {
        title: "状态",
        key: "status",
        width: 50,
        align: "center",
        render: (u, w) => {
          if (w.passes) {
            const W = ie ? e.createElement(ie, {
              style: { color: "#52c41a", fontSize: 18 }
            }) : "✅";
            return e.createElement(L, { title: "已完成" }, W);
          }
          const p = oe ? e.createElement(oe, {
            style: { color: "#faad14", fontSize: 18 }
          }) : "🕐";
          return e.createElement(L, { title: "待处理" }, p);
        }
      },
      {
        title: "ID",
        dataIndex: "id",
        key: "id",
        width: 85,
        render: (u) => e.createElement(M, { color: "blue" }, u)
      },
      {
        title: "标题",
        dataIndex: "title",
        key: "title",
        render: (u) => e.createElement(j, { strong: !0 }, u)
      },
      {
        title: "优先级",
        key: "priority",
        width: 70,
        render: (u, w) => {
          const p = w.priority;
          return e.createElement(
            M,
            { color: "default" },
            p != null ? String(p) : "-"
          );
        }
      },
      {
        title: "描述",
        dataIndex: "description",
        key: "description",
        ellipsis: !0
      },
      {
        title: "验收标准",
        key: "acceptance",
        width: 200,
        render: (u, w) => {
          const p = w.acceptanceCriteria;
          return typeof p == "string" ? e.createElement(
            "div",
            {
              style: { fontSize: 12, color: "#666", whiteSpace: "pre-wrap" }
            },
            p.length > 100 ? p.slice(0, 100) + "..." : p
          ) : Array.isArray(p) ? e.createElement(
            "div",
            { style: { fontSize: 12, color: "#666" } },
            p.length > 2 ? p.slice(0, 2).join(", ") + "..." : p.join(", ")
          ) : "-";
        }
      }
    ], q = e.createElement(
      F,
      { size: 8 },
      _e ? e.createElement(_e, { style: { color: "#1677ff" } }) : null,
      e.createElement(
        "span",
        { style: { fontSize: 14 } },
        e.createElement(j, { strong: !0 }, n.project || "PRD")
      )
    ), H = e.createElement(D, {
      columns: V,
      dataSource: ge.map((u) => ({ ...u, key: u.id })),
      size: "small",
      pagination: !1,
      scroll: { x: "max-content" },
      style: { marginBottom: 4 }
    });
    return e.createElement(
      "div",
      {
        style: {
          width: "100%",
          borderRadius: 10,
          border: "1px solid #f0f0f0",
          overflow: "hidden",
          background: "#fff",
          padding: "12px 16px",
          margin: "4px 0"
        }
      },
      e.createElement("div", { style: { marginBottom: 8 } }, q),
      e.createElement(g, {
        size: "small",
        column: { xs: 1, sm: 2, md: 3 },
        style: { marginBottom: 12 },
        bordered: !1,
        items: [
          {
            key: "progress",
            label: "进度",
            children: `${G}/${ee.length} 完成`
          }
        ]
      }),
      H,
      e.createElement(
        "div",
        {
          style: {
            fontSize: 11,
            color: "#8c8c8c",
            display: "flex",
            alignItems: "center",
            gap: 8
          }
        },
        ie ? e.createElement(ie, {
          style: { color: "#52c41a", fontSize: 14 }
        }) : "✅",
        e.createElement("span", null, "已完成"),
        e.createElement("span", { style: { margin: "0 4px" } }, "·"),
        oe ? e.createElement(oe, {
          style: { color: "#faad14", fontSize: 14 }
        }) : "🕐",
        e.createElement("span", null, "待处理")
      )
    );
  }
  const {
    Form: ce,
    Select: Re,
    Drawer: et,
    Modal: mt,
    Empty: _t,
    Badge: gt,
    Divider: Rt,
    message: ae
  } = P, {
    ApiOutlined: ht,
    PlusOutlined: yt,
    ReloadOutlined: tt,
    DeleteOutlined: Et,
    LinkOutlined: xt,
    DisconnectOutlined: Vt
  } = N || {}, { useEffect: wt } = e, De = "/a2a/agents";
  function nt() {
    var t;
    try {
      const n = sessionStorage.getItem("jotaduo-agent-storage") || localStorage.getItem("jotaduo-agent-storage");
      if (n) {
        const o = JSON.parse(n);
        return ((t = o == null ? void 0 : o.state) == null ? void 0 : t.selectedAgent) || null;
      }
    } catch {
    }
    return null;
  }
  async function Le(t, n) {
    const o = O(t), i = X == null ? void 0 : X(), d = nt(), h = {
      "Content-Type": "application/json",
      ...i ? { Authorization: `Bearer ${i}` } : {},
      ...d ? { "X-Agent-Id": d } : {}
    }, a = await fetch(o, {
      ...n,
      headers: { ...h, ...(n == null ? void 0 : n.headers) || {} }
    });
    if (!a.ok) {
      const c = await a.text().catch(() => "");
      throw new Error(c || `HTTP ${a.status}`);
    }
    return a.status === 204 || a.headers.get("content-length") === "0" ? null : a.json();
  }
  function zt(t) {
    var c;
    const { agent: n, onClick: o } = t, i = n.status === "connected", d = i ? "#52c41a" : n.status === "error" ? "#ff4d4f" : "#d9d9d9", h = i ? "已连接" : n.status === "error" ? "错误" : "未连接", a = {
      gateway: "阿里云Agent Hub",
      bearer: "Bearer Token",
      api_key: "API Key"
    };
    return e.createElement(
      Z,
      {
        hoverable: !0,
        onClick: o,
        size: "small",
        style: { cursor: "pointer" },
        title: e.createElement(
          F,
          null,
          e.createElement(gt, { color: d }),
          e.createElement(
            "span",
            null,
            n.alias || n.name || n.url
          )
        ),
        extra: n.auth_type ? e.createElement(
          M,
          { color: "blue" },
          a[n.auth_type] || n.auth_type
        ) : null
      },
      e.createElement(
        "div",
        { style: { fontSize: 12, color: "#666" } },
        e.createElement(
          "div",
          { style: { marginBottom: 4 } },
          xt ? e.createElement(xt, { style: { marginRight: 4 } }) : null,
          n.url
        ),
        n.description ? e.createElement(
          "div",
          { style: { marginBottom: 4, color: "#999" } },
          n.description
        ) : null,
        ((c = n.skills) == null ? void 0 : c.length) > 0 ? e.createElement(
          "div",
          null,
          n.skills.slice(0, 3).map(
            (l, R) => e.createElement(
              M,
              { key: R, style: { fontSize: 11 } },
              l.name
            )
          ),
          n.skills.length > 3 ? e.createElement(
            M,
            { style: { fontSize: 11 } },
            `+${n.skills.length - 3}`
          ) : null
        ) : null,
        e.createElement(
          "div",
          { style: { marginTop: 4, color: d, fontSize: 11 } },
          h,
          n.error ? ` - ${n.error}` : ""
        )
      )
    );
  }
  function $t() {
    const t = e.useRef(nt()), [n, o] = b(t.current);
    return wt(() => {
      const i = () => {
        const h = nt();
        h !== t.current && (t.current = h, o(h));
      }, d = setInterval(i, 200);
      return window.addEventListener("storage", i), () => {
        clearInterval(d), window.removeEventListener("storage", i);
      };
    }, []), n;
  }
  function Pt() {
    var vt, Ct;
    const { token: t } = Q.useToken(), n = $t(), [o, i] = b([]), [d, h] = b(!0), [a, c] = b(!1), [l, R] = b(null), [k, $] = b(!1), [ee, ge] = b(!1), [G, V] = b(!1), [q, H] = b(!1), [u, w] = b(""), [p] = ce.useForm(), [W, Be] = b(!1), [ue, Ae] = b(!1), [te, ke] = b([]), [de, he] = b(
      /* @__PURE__ */ new Set()
    ), [je, ve] = b(
      []
    ), ye = e.useRef(null), ze = (r) => !r || !r.trim() ? null : /\s/.test(r) ? "别名不能包含空格" : null, K = se(
      () => new Set(o.map((r) => r.url)),
      [o]
    ), Ce = e.useRef(K);
    Ce.current = K;
    const f = T(async () => {
      h(!0);
      try {
        const r = await Le(De);
        i((r == null ? void 0 : r.agents) || []);
      } catch {
        i([]);
      } finally {
        h(!1);
      }
    }, []);
    wt(() => {
      f();
    }, [n]);
    const v = T(() => {
      $(!0), R(null), c(!0), p.resetFields(), p.setFieldsValue({
        url: "",
        alias: "",
        auth_type: "",
        auth_token: ""
      });
    }, [p]), x = T((r) => {
      $(!1), R(r), c(!0);
    }, []), s = T(() => {
      H(!1), w("");
    }, []), y = T(async () => {
      if (!l || !u.trim()) return;
      const r = ze(u);
      if (r) {
        ae.error(r);
        return;
      }
      const E = l.alias || l.url, S = u.trim();
      if (S === E) {
        s();
        return;
      }
      try {
        const Se = await Le(
          `${De}?alias=${encodeURIComponent(E)}`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ new_alias: S })
          }
        );
        ae.success("别名已修改"), H(!1), R(Se), await f();
      } catch (Se) {
        ae.error(Se.message || "修改失败");
      }
    }, [l, u, f, s]), m = T(() => {
      s(), c(!1), R(null), $(!1), p.resetFields();
    }, [s, p]), A = T(async () => {
      let r;
      try {
        r = await p.validateFields();
      } catch {
        return;
      }
      const E = {
        url: String(r.url || "").trim(),
        alias: String(r.alias || "").trim() || void 0,
        auth_type: String(r.auth_type || ""),
        auth_token: String(r.auth_token || "")
      };
      if (E.url) {
        ge(!0);
        try {
          await Le(De, {
            method: "POST",
            body: JSON.stringify(E)
          }), ae.success("A2A Agent 注册成功"), await f(), m();
        } catch (S) {
          ae.error(S.message || "注册失败");
        } finally {
          ge(!1);
        }
      }
    }, [p, f, m]), C = T(async () => {
      if (!l) return;
      const r = l.alias || l.url, E = l.name || r;
      mt.confirm({
        title: "确认删除",
        content: `确定删除 A2A Agent「${E}」吗？此操作不可撤销。`,
        okText: "删除",
        cancelText: "取消",
        okButtonProps: { danger: !0 },
        async onOk() {
          try {
            await Le(`${De}?alias=${encodeURIComponent(r)}`, {
              method: "DELETE"
            }), ae.success(`已删除 A2A Agent「${E}」`), await f(), m();
          } catch (S) {
            ae.error(S.message || "删除失败");
          }
        }
      });
    }, [l, f, m]), we = T(async () => {
      if (!l) return;
      const r = l.alias || l.url;
      V(!0);
      try {
        const E = await Le(
          `${De}/refresh?alias=${encodeURIComponent(r)}`,
          {
            method: "POST"
          }
        );
        ae.success("Agent Card 已刷新"), await f(), E && R(E);
      } catch (E) {
        ae.error(E.message || "刷新失败");
      } finally {
        V(!1);
      }
    }, [l, f]), J = T(() => {
      l && (w(l.alias || ""), H(!0));
    }, [l]), Y = T(() => {
      Be(!0), ke([]), he(/* @__PURE__ */ new Set()), ve([]), ye.current = null, Ee();
    }, []), pe = T(() => {
      ue && ye.current && ye.current.abort(), Be(!1), ke([]), he(/* @__PURE__ */ new Set()), ve([]), ye.current = null;
    }, [ue]), Ee = T(async () => {
      Ae(!0);
      const r = new AbortController();
      ye.current = r;
      try {
        const E = X == null ? void 0 : X(), S = nt(), Se = {
          ...E ? { Authorization: `Bearer ${E}` } : {},
          ...S ? { "X-Agent-Id": S } : {}
        }, We = await fetch(O("/a2a/import"), {
          method: "GET",
          headers: Se,
          signal: r.signal
        });
        if (!We.ok) {
          const Xe = await We.text().catch(() => "");
          throw new Error(Xe || `HTTP ${We.status}`);
        }
        const ut = await We.json(), pt = (ut == null ? void 0 : ut.agents) || [];
        if (pt.length === 0) {
          ae.warning("未找到可用的 Agent");
          return;
        }
        ke(pt);
        const Ft = Ce.current;
        he(
          new Set(
            pt.filter((Xe) => !Ft.has(Xe.url)).map((Xe) => Xe.url)
          )
        );
      } catch (E) {
        if ((E == null ? void 0 : E.name) === "AbortError") return;
        ae.error(E.message || "获取 Agent 列表失败");
      } finally {
        Ae(!1), ye.current = null;
      }
    }, []), Te = T((r) => {
      he((E) => {
        const S = new Set(E);
        return S.has(r) ? S.delete(r) : S.add(r), S;
      });
    }, []), I = T(() => {
      he(
        new Set(
          te.filter((r) => !K.has(r.url)).map((r) => r.url)
        )
      );
    }, [te, K]), fe = T(() => {
      he(/* @__PURE__ */ new Set());
    }, []), rt = T(async () => {
      const r = te.filter(
        (S) => de.has(S.url) && !K.has(S.url)
      );
      if (r.length === 0) {
        ae.warning("请至少选择一个 Agent");
        return;
      }
      Ae(!0), ve([]);
      const E = [];
      for (const S of r) {
        try {
          await Le(De, {
            method: "POST",
            body: JSON.stringify({
              url: S.url,
              alias: S.name || void 0,
              auth_type: S.auth_type || "gateway",
              auth_token: ""
            })
          }), E.push({ name: S.name || S.url, success: !0 });
        } catch (Se) {
          E.push({
            name: S.name || S.url,
            success: !1,
            error: Se.message || "注册失败"
          });
        }
        ve([...E]);
      }
      await f(), ae.success(
        `导入完成：成功 ${E.filter((S) => S.success).length} 个，失败 ${E.filter((S) => !S.success).length} 个`
      ), Ae(!1), setTimeout(() => pe(), 800);
    }, [te, de, f, K]), Ye = ((vt = ce.useWatch) == null ? void 0 : vt.call(ce, "auth_type", p)) ?? "", dt = e.createElement(
      ce,
      { form: p, layout: "vertical" },
      e.createElement(
        ce.Item,
        {
          name: "url",
          label: "Agent URL",
          rules: [{ required: !0, message: "请输入 Agent URL" }]
        },
        e.createElement(le, {
          placeholder: "https://agent.example.com"
        })
      ),
      e.createElement(
        ce.Item,
        {
          name: "alias",
          label: "别名",
          rules: [
            {
              validator: (r, E) => {
                const S = ze(E);
                return S ? Promise.reject(new Error(S)) : Promise.resolve();
              }
            }
          ]
        },
        e.createElement(le, {
          placeholder: "输入别名（可选，仅小写字母、数字和连字符）"
        })
      ),
      e.createElement(
        ce.Item,
        { name: "auth_type", label: "认证类型" },
        e.createElement(
          Re,
          { allowClear: !0, placeholder: "无认证" },
          e.createElement(
            Re.Option,
            { value: "bearer" },
            "Bearer Token"
          ),
          e.createElement(Re.Option, { value: "api_key" }, "API Key"),
          e.createElement(
            Re.Option,
            { value: "gateway" },
            "阿里云Agent Hub"
          )
        )
      ),
      Ye === "gateway" ? e.createElement(
        "div",
        {
          style: {
            marginBottom: 16,
            padding: "8px 12px",
            background: "#f6ffed",
            border: "1px solid #b7eb8f",
            borderRadius: 6,
            fontSize: 12,
            color: "#52c41a"
          }
        },
        "阿里云Agent Hub 模式将自动使用环境变量中的 AK-SK 换取 Bearer Token"
      ) : null,
      Ye && Ye !== "gateway" ? e.createElement(
        ce.Item,
        { name: "auth_token", label: "认证凭证" },
        e.createElement(le.Password, {
          placeholder: "Bearer Token 或 API Key"
        })
      ) : null
    ), Bt = l ? e.createElement(
      "div",
      null,
      e.createElement(
        g,
        { column: 1, bordered: !0, size: "small" },
        e.createElement(
          g.Item,
          { label: "URL" },
          l.url
        ),
        e.createElement(
          g.Item,
          { label: "别名" },
          q ? e.createElement(
            "div",
            {
              style: { display: "flex", alignItems: "center", gap: 6 }
            },
            e.createElement(le, {
              value: u,
              onChange: (r) => w(r.target.value),
              onPressEnter: y,
              autoFocus: !0,
              placeholder: "输入新别名",
              size: "small",
              style: { flex: 1 }
            }),
            e.createElement(
              _,
              {
                type: "link",
                size: "small",
                onClick: y,
                disabled: !u.trim(),
                style: { padding: 0 }
              },
              "保存"
            )
          ) : e.createElement(
            "div",
            {
              style: { display: "flex", alignItems: "center", gap: 8 }
            },
            e.createElement("span", null, l.alias || "-"),
            e.createElement(
              "a",
              {
                style: { fontSize: 12 },
                onClick: J
              },
              "修改"
            )
          )
        ),
        e.createElement(
          g.Item,
          { label: "Agent 名称" },
          l.name || "-"
        ),
        e.createElement(
          g.Item,
          { label: "状态" },
          e.createElement(gt, {
            color: l.status === "connected" ? "#52c41a" : l.status === "error" ? "#ff4d4f" : "#d9d9d9",
            text: l.status === "connected" ? "已连接" : l.status === "error" ? "错误" : "未连接"
          })
        ),
        e.createElement(
          g.Item,
          { label: "认证类型" },
          l.auth_type ? e.createElement(
            M,
            { color: "blue" },
            {
              gateway: "阿里云Agent Hub",
              bearer: "Bearer Token",
              api_key: "API Key"
            }[l.auth_type] || l.auth_type
          ) : "无认证"
        ),
        e.createElement(
          g.Item,
          { label: "描述" },
          l.description || "-"
        ),
        e.createElement(
          g.Item,
          { label: "版本" },
          l.version || "-"
        )
      ),
      ((Ct = l.skills) == null ? void 0 : Ct.length) > 0 ? e.createElement(
        "div",
        { style: { marginTop: 16 } },
        e.createElement("h4", null, "技能"),
        ...l.skills.map(
          (r, E) => e.createElement(
            Z,
            { key: E, size: "small", style: { marginBottom: 8 } },
            e.createElement("strong", null, r.name),
            r.description ? e.createElement(
              "div",
              { style: { color: "#666", fontSize: 12 } },
              r.description
            ) : null
          )
        )
      ) : null,
      l.capabilities ? e.createElement(
        "div",
        { style: { marginTop: 16 } },
        e.createElement("h4", null, "能力"),
        e.createElement(
          F,
          null,
          e.createElement(
            M,
            {
              color: l.capabilities.streaming ? "green" : "default"
            },
            "Streaming"
          ),
          e.createElement(
            M,
            {
              color: l.capabilities.push_notifications ? "green" : "default"
            },
            "Push Notifications"
          )
        )
      ) : null,
      l.error ? e.createElement(
        "div",
        {
          style: {
            marginTop: 16,
            padding: "8px 12px",
            background: "#fff2f0",
            border: "1px solid #ffccc7",
            borderRadius: 6,
            fontSize: 12,
            color: "#ff4d4f"
          }
        },
        l.error
      ) : null,
      e.createElement(Rt, null),
      e.createElement(
        F,
        null,
        e.createElement(
          _,
          {
            type: "primary",
            icon: tt ? e.createElement(tt) : null,
            loading: G,
            onClick: we
          },
          "刷新 Agent Card"
        ),
        e.createElement(
          _,
          {
            danger: !0,
            icon: Et ? e.createElement(Et) : null,
            onClick: C
          },
          "删除"
        )
      )
    ) : null, jt = e.createElement(
      et,
      {
        title: k ? "注册远程 A2A Agent" : (l == null ? void 0 : l.name) || (l == null ? void 0 : l.alias) || "Agent 详情",
        open: a,
        onClose: m,
        width: 480,
        footer: k ? e.createElement(
          F,
          { style: { display: "flex", justifyContent: "flex-end" } },
          e.createElement(_, { onClick: m }, "取消"),
          e.createElement(
            _,
            { type: "primary", loading: ee, onClick: A },
            "注册"
          )
        ) : null
      },
      k ? dt : Bt
    ), Ht = e.createElement(
      "div",
      { style: { marginBottom: 16 } },
      e.createElement(
        "div",
        {
          style: {
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }
        },
        e.createElement("h2", { style: { margin: 0 } }, "A2A 远程 Agent"),
        e.createElement(
          F,
          null,
          e.createElement(
            _,
            {
              icon: tt ? e.createElement(tt) : null,
              onClick: f,
              loading: d
            },
            "刷新列表"
          ),
          e.createElement(
            _,
            {
              icon: ht ? e.createElement(ht) : null,
              onClick: Y
            },
            "从阿里云AgentHub导入"
          ),
          e.createElement(
            _,
            {
              type: "primary",
              icon: yt ? e.createElement(yt) : null,
              onClick: v
            },
            "注册 Agent"
          )
        )
      ),
      e.createElement(
        "div",
        {
          style: {
            marginTop: 8,
            fontSize: 12,
            color: "#8c8c8c",
            lineHeight: 1.6
          }
        },
        me ? e.createElement(me, {
          style: { marginRight: 4, color: "#faad14" }
        }) : null,
        "当前 A2A 功能仅支持 CloudPaw 插件连接阿里云 Skills 门户 Agent，连接其他 Agent 可能存在不兼容问题。"
      )
    ), Wt = d ? e.createElement(
      "div",
      { style: { textAlign: "center", padding: 60 } },
      e.createElement(z, { size: "large" })
    ) : o.length === 0 ? e.createElement(_t, {
      description: "暂无注册的远程 A2A Agent"
    }) : e.createElement(
      "div",
      {
        style: {
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
          gap: 12
        }
      },
      ...o.map(
        (r) => e.createElement(zt, {
          key: r.alias || r.url,
          agent: r,
          onClick: () => x(r)
        })
      )
    ), He = je.length > 0, Jt = e.createElement(
      mt,
      {
        title: He ? "导入结果" : "从阿里云AgentHub导入 Agent",
        open: W,
        onCancel: pe,
        closable: !ue || He,
        maskClosable: !ue || He,
        width: 800,
        footer: He ? e.createElement(
          F,
          { style: { display: "flex", justifyContent: "flex-end" } },
          e.createElement(
            _,
            { type: "primary", onClick: pe },
            "关闭"
          )
        ) : te.length > 0 ? e.createElement(
          F,
          { style: { display: "flex", justifyContent: "flex-end" } },
          e.createElement(
            _,
            { onClick: pe },
            "取消"
          ),
          e.createElement(
            _,
            {
              type: "primary",
              loading: ue,
              disabled: de.size === 0,
              onClick: rt
            },
            `确认导入 (${de.size}/${te.length})`
          )
        ) : null
      },
      // Loading state
      ue && te.length === 0 && e.createElement(
        "div",
        {
          style: {
            textAlign: "center",
            padding: 40,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 12
          }
        },
        e.createElement(z, { size: "large" }),
        e.createElement(
          "span",
          { style: { fontSize: 13, color: t.colorTextTertiary } },
          "正在从 AgentHub 获取 Agent 列表..."
        )
      ),
      // Agent selection list (hide after import completed)
      !ue && !He && te.length > 0 && e.createElement(
        "div",
        null,
        // Header bar
        e.createElement(
          "div",
          {
            style: {
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
              fontSize: 12,
              color: t.colorTextTertiary
            }
          },
          e.createElement(
            "span",
            null,
            `共 ${te.length} 个 Agent，已选 ${de.size} 个`
          ),
          e.createElement(
            F,
            { size: 4 },
            e.createElement(
              _,
              {
                size: "small",
                type: "link",
                style: { padding: 0, height: "auto" },
                onClick: I
              },
              "全选"
            ),
            e.createElement(
              _,
              {
                size: "small",
                type: "link",
                style: { padding: 0, height: "auto" },
                onClick: fe
              },
              "取消全选"
            )
          )
        ),
        // Agent list
        e.createElement(
          "div",
          {
            style: {
              display: "flex",
              flexDirection: "column",
              gap: 8,
              maxHeight: 420,
              overflowY: "auto"
            }
          },
          ...te.map((r) => {
            var S;
            const E = de.has(r.url);
            return e.createElement(
              "div",
              {
                key: r.url,
                style: {
                  display: "flex",
                  gap: 8,
                  padding: 10,
                  border: E ? `1px solid ${t.colorInfo}` : `1px solid ${t.colorBorderSecondary}`,
                  borderRadius: 6,
                  cursor: K.has(r.url) ? "default" : "pointer",
                  background: K.has(r.url) ? t.colorBgLayout : E ? t.colorInfoBg : t.colorBgContainer,
                  transition: "all 0.15s ease",
                  opacity: K.has(r.url) ? 0.7 : 1
                },
                onClick: () => {
                  K.has(r.url) || Te(r.url);
                }
              },
              e.createElement(
                "div",
                { style: { flex: 1, minWidth: 0 } },
                e.createElement(
                  "div",
                  {
                    style: {
                      fontWeight: 500,
                      fontSize: 13,
                      marginBottom: 2
                    }
                  },
                  r.name || r.url
                ),
                r.description ? e.createElement(
                  "div",
                  {
                    style: {
                      fontSize: 11,
                      color: t.colorTextTertiary,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap"
                    }
                  },
                  r.description
                ) : null,
                ((S = r.skills) == null ? void 0 : S.length) > 0 ? e.createElement(
                  "div",
                  { style: { marginTop: 4 } },
                  ...r.skills.slice(0, 3).map(
                    (Se, We) => e.createElement(
                      M,
                      {
                        key: We,
                        color: t.colorInfoHover,
                        style: {
                          fontSize: 10,
                          marginRight: 4,
                          fontWeight: 500
                        }
                      },
                      Se.name
                    )
                  ),
                  r.skills.length > 3 ? e.createElement(
                    M,
                    { style: { fontSize: 10 } },
                    `+${r.skills.length - 3}`
                  ) : null
                ) : null
              ),
              K.has(r.url) ? e.createElement(
                M,
                {
                  color: t.colorSuccess,
                  style: {
                    fontWeight: 600,
                    fontSize: 11,
                    flexShrink: 0,
                    padding: "2px 8px",
                    lineHeight: "18px",
                    height: 22,
                    borderRadius: 4
                  }
                },
                "✓ 已导入"
              ) : null
            );
          })
        )
      ),
      // Import results
      He && e.createElement(
        "div",
        {
          style: {
            maxHeight: 350,
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: 6
          }
        },
        ...je.map(
          (r, E) => e.createElement(
            "div",
            {
              key: E,
              style: {
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 10px",
                borderRadius: 4,
                background: r.success ? t.colorInfoBg : t.colorErrorBg,
                border: r.success ? `1px solid ${t.colorInfo}` : `1px solid ${t.colorErrorBorder}`,
                fontSize: 12
              }
            },
            e.createElement(
              "span",
              {
                style: {
                  color: r.success ? t.colorSuccess : t.colorError,
                  fontSize: 14
                }
              },
              r.success ? "✓" : "✗"
            ),
            e.createElement(
              "span",
              {
                style: {
                  flex: 1,
                  color: r.success ? t.colorText : t.colorError
                }
              },
              r.name,
              r.error ? ` - ${r.error}` : ""
            )
          )
        )
      )
    );
    return e.createElement(
      "div",
      { style: { padding: 24 } },
      Ht,
      Wt,
      jt,
      Jt
    );
  }
  function Ot({ data: t }) {
    var ze, K, Ce;
    const { token: n } = Q.useToken(), o = e.useRef(null), [i, d] = b({}), h = se(() => {
      var v, x, s;
      const f = (s = (x = (v = t == null ? void 0 : t.content) == null ? void 0 : v[0]) == null ? void 0 : x.data) == null ? void 0 : s.arguments;
      if (!f) return null;
      try {
        return JSON.parse(f);
      } catch {
        return null;
      }
    }, [(Ce = (K = (ze = t == null ? void 0 : t.content) == null ? void 0 : ze[0]) == null ? void 0 : K.data) == null ? void 0 : Ce.arguments]), { toolResult: a, rawErrorText: c } = se(() => {
      var v;
      const f = t == null ? void 0 : t.content;
      if (!Array.isArray(f))
        return { toolResult: null, rawErrorText: "" };
      for (const x of f) {
        const s = (v = x == null ? void 0 : x.data) == null ? void 0 : v.output;
        if (!s) continue;
        let y = "";
        if (Array.isArray(s)) {
          const m = s.find(
            (A) => (A == null ? void 0 : A.type) === "text" && (A == null ? void 0 : A.text)
          );
          y = (m == null ? void 0 : m.text) || "";
        } else if (typeof s == "string")
          try {
            const m = JSON.parse(s);
            if (typeof m == "object" && (m != null && m.steps || m != null && m.response_text))
              return { toolResult: m, rawErrorText: "" };
            if (Array.isArray(m)) {
              const A = m.find((C) => (C == null ? void 0 : C.type) === "text" && (C == null ? void 0 : C.text));
              A != null && A.text && (y = A.text);
            }
          } catch {
            y = s;
          }
        if (y)
          try {
            return { toolResult: JSON.parse(y), rawErrorText: "" };
          } catch {
            return { toolResult: null, rawErrorText: y };
          }
      }
      return { toolResult: null, rawErrorText: "" };
    }, [t == null ? void 0 : t.content]), l = (a == null ? void 0 : a.steps) || [], R = (a == null ? void 0 : a.task_state) || "", k = (a == null ? void 0 : a.error) || "", $ = (a == null ? void 0 : a.response_text) || "", ee = (a == null ? void 0 : a.context_id) || "";
    e.useEffect(() => {
      o.current && (o.current.scrollTop = o.current.scrollHeight);
    }, [l.length, $, c]), e.useEffect(() => {
      const f = { ...i };
      let v = !1;
      l.forEach((x, s) => {
        i[s] === void 0 && (x.type === "thinking" && x.done || x.type === "tool_call" && x.status !== "running") && (f[s] = !0, v = !0);
      }), v && d(f);
    }, [l]);
    const ge = (h == null ? void 0 : h.agent_alias) || "", G = (h == null ? void 0 : h.agent_url) || "", V = ge || G || "远程 Agent", q = {
      completed: { color: "#52c41a", text: "已完成" },
      TASK_STATE_COMPLETED: { color: "#52c41a", text: "已完成" },
      failed: { color: "#ff4d4f", text: "失败" },
      TASK_STATE_FAILED: { color: "#ff4d4f", text: "失败" },
      error: { color: "#ff4d4f", text: "出错" },
      canceled: { color: "#faad14", text: "已取消" },
      TASK_STATE_CANCELED: { color: "#faad14", text: "已取消" },
      AWAITING_USER_INPUT: { color: "#1677ff", text: "等待输入" },
      input_required: { color: "#1677ff", text: "等待输入" }
    }, w = (a !== null || !!c) && !(R === "working" || R === "TASK_STATE_WORKING");
    let p = "#1677ff", W = "执行中...";
    w && (q[R] ? (p = q[R].color, W = q[R].text) : c ? (p = "#ff4d4f", W = "出错") : (p = "#52c41a", W = "已完成"));
    const Be = e.createElement(
      F,
      { size: 6 },
      e.createElement("span", { style: { fontSize: 13 } }, "🔗"),
      e.createElement(
        j,
        { style: { fontSize: 12, color: "#595959" } },
        `A2A: ${V}`
      ),
      e.createElement(
        M,
        { color: p, style: { fontSize: 11, lineHeight: "18px" } },
        W
      )
    ), ue = ee ? e.createElement(
      "div",
      {
        style: {
          fontSize: 10,
          fontFamily: "monospace",
          maxWidth: "100%",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          lineHeight: "16px",
          padding: "2px 8px",
          borderRadius: 4,
          marginBottom: 6,
          background: n.colorBgLayout,
          color: n.colorTextSecondary
        }
      },
      `contextId: ${ee}`
    ) : null, Ae = [Be, ue], te = l.length === 0 && !c && !k, ke = !w && te ? e.createElement(
      "div",
      {
        style: {
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "6px 10px",
          marginBottom: 8,
          background: "#f6ffed",
          border: "1px solid #b7eb8f",
          borderRadius: 6
        }
      },
      e.createElement(z, { size: "small" }),
      e.createElement(
        j,
        { style: { fontSize: 12, color: "#52c41a" } },
        `正在连接 ${V}...`
      )
    ) : null;
    function de(f) {
      d((v) => ({
        ...v,
        [f]: !v[f]
      }));
    }
    function he(f, v) {
      const x = !!i[v];
      if (f.type === "thinking") {
        const s = !!f.done, y = s ? "💭" : "🧠", m = s ? "思考完成" : "思考中...", A = e.createElement(
          "div",
          {
            key: `step-${v}`,
            style: {
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "3px 0",
              cursor: s ? "pointer" : "default",
              fontSize: 12,
              color: "#8c8c8c"
            },
            onClick: s ? () => de(v) : void 0
          },
          s && e.createElement(
            "span",
            { style: { fontSize: 10, color: "#bfbfbf" } },
            x ? "▶" : "▼"
          ),
          e.createElement("span", null, y),
          e.createElement("span", null, m),
          !s && e.createElement(z, {
            size: "small",
            style: { marginLeft: 4 }
          })
        );
        return x ? A : e.createElement(
          "div",
          { key: `step-${v}` },
          A,
          e.createElement(
            "div",
            {
              style: {
                marginLeft: 20,
                padding: "4px 8px",
                background: "#fafafa",
                borderRadius: 4,
                fontSize: 12,
                color: "#595959",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                maxHeight: 120,
                overflowY: "auto",
                lineHeight: "1.5"
              }
            },
            f.text || ""
          )
        );
      }
      if (f.type === "tool_call") {
        const s = f.status === "running", y = f.status === "error", m = s ? "⚙️" : y ? "❌" : "✅", A = s ? `正在执行: ${f.name}` : y ? `执行失败: ${f.name}` : `执行完成: ${f.name}`, C = s ? "#1677ff" : y ? "#ff4d4f" : "#52c41a", we = e.createElement(
          "div",
          {
            key: `step-${v}`,
            style: {
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "3px 0",
              cursor: s ? "default" : "pointer",
              fontSize: 12,
              color: C
            },
            onClick: s ? void 0 : () => de(v)
          },
          !s && e.createElement(
            "span",
            { style: { fontSize: 10, color: "#bfbfbf" } },
            x ? "▶" : "▼"
          ),
          e.createElement("span", null, m),
          e.createElement("span", null, A),
          s && e.createElement(z, {
            size: "small",
            style: { marginLeft: 4 }
          })
        );
        return x || !f.desc && !s ? we : e.createElement(
          "div",
          { key: `step-${v}` },
          we,
          f.desc && e.createElement(
            "div",
            {
              style: {
                marginLeft: 20,
                padding: "2px 8px",
                fontSize: 11,
                color: "#8c8c8c"
              }
            },
            f.desc
          )
        );
      }
      return f.type === "text" ? e.createElement(
        "div",
        {
          key: `step-${v}`,
          style: {
            padding: "4px 0",
            fontSize: 12,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            lineHeight: "1.6",
            color: "#262626"
          }
        },
        f.text || ""
      ) : null;
    }
    const je = l.length > 0 ? e.createElement(
      "div",
      {
        ref: o,
        style: {
          background: "#fafafa",
          border: "1px solid #e8e8e8",
          borderRadius: 6,
          padding: "6px 10px",
          maxHeight: 200,
          overflowY: "auto"
        }
      },
      ...l.map(he)
    ) : null, ve = c || k ? e.createElement(
      "div",
      {
        style: {
          background: "#fff2f0",
          border: "1px solid #ffccc7",
          borderRadius: 6,
          padding: "8px 12px",
          fontSize: 12,
          color: "#ff4d4f",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word"
        }
      },
      k ? `错误: ${k}` : c
    ) : null, ye = !l.length && $ && !c ? e.createElement(
      "div",
      {
        ref: o,
        style: {
          background: "#fafafa",
          border: "1px solid #e8e8e8",
          borderRadius: 6,
          padding: "10px 12px",
          maxHeight: 200,
          overflowY: "auto"
        }
      },
      e.createElement(
        j,
        {
          style: {
            fontSize: 12,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            lineHeight: "1.6"
          }
        },
        $
      )
    ) : null;
    return e.createElement(
      "div",
      {
        style: {
          width: "100%",
          borderRadius: 8,
          border: "1px solid #f0f0f0",
          overflow: "hidden",
          background: "#fff",
          padding: "8px 12px",
          margin: "4px 0"
        }
      },
      e.createElement(
        "div",
        { style: { marginBottom: 6 } },
        ...Ae
      ),
      ke,
      je,
      ye,
      ve
    );
  }
  const Mt = "__A2A_STREAM_START__", Nt = "A2A_STREAM_START", Ke = /* @__PURE__ */ new Set();
  function st(t) {
    return t ? t.includes(Mt) || t.includes(Nt) : !1;
  }
  function it(t) {
    var n, o;
    return t.getAttribute("data-msg-id") || t.getAttribute("data-message-id") || ((n = t.closest("[data-msg-id]")) == null ? void 0 : n.getAttribute("data-msg-id")) || ((o = t.closest("[data-message-id]")) == null ? void 0 : o.getAttribute("data-message-id")) || null;
  }
  function Dt(t) {
    if (st(t.innerHTML) || st(t.textContent))
      return t;
    const n = document.createTreeWalker(
      t,
      NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT
    );
    for (; n.nextNode(); ) {
      const o = n.currentNode, i = o.nodeType === Node.TEXT_NODE ? o.textContent : o.innerHTML;
      if (st(i)) {
        const d = o.nodeType === Node.TEXT_NODE ? o.parentElement : o;
        if (d) return d;
      }
    }
    return null;
  }
  async function ct(t) {
    var l, R;
    const n = window.JotaDuo;
    if (!(n != null && n.host)) {
      console.warn("[a2a] JotaDuo.host not available");
      return;
    }
    const { getApiUrl: o, getApiToken: i } = n.host, d = o("/a2a/call/stream"), h = i();
    console.log("[a2a] Subscribing to SSE stream:", d);
    const a = document.createElement("div");
    a.style.cssText = "background:#f6ffed;border:1px solid #b7eb8f;border-radius:8px;padding:12px 16px;margin:4px 0;font-size:13px;white-space:pre-wrap;word-break:break-word;color:#262626;min-height:24px;", a.textContent = "正在连接远程 Agent...", t.textContent = "", t.appendChild(a);
    const c = new AbortController();
    try {
      const k = {
        Accept: "text/event-stream"
      };
      h && (k.Authorization = `Bearer ${h}`);
      try {
        const V = sessionStorage.getItem("jotaduo-agent-storage") || localStorage.getItem("jotaduo-agent-storage"), q = (R = (l = JSON.parse(V || "{}")) == null ? void 0 : l.state) == null ? void 0 : R.selectedAgent;
        q && (k["X-Agent-Id"] = q);
      } catch {
      }
      console.log("[a2a] Fetching SSE with headers:", k);
      const $ = await fetch(d, { headers: k, signal: c.signal });
      if (console.log("[a2a] SSE response status:", $.status), !$.ok) {
        const V = await $.text().catch(() => "");
        a.textContent = `SSE 连接失败 (${$.status}): ${V.slice(
          0,
          100
        )}`, a.style.borderColor = "#ff4d4f", a.style.background = "#fff1f0";
        return;
      }
      if (!$.body) {
        a.textContent = "SSE 连接失败：无响应体", a.style.borderColor = "#ff4d4f", a.style.background = "#fff1f0";
        return;
      }
      const ee = $.body.getReader(), ge = new TextDecoder();
      let G = "";
      for (; ; ) {
        const { done: V, value: q } = await ee.read();
        if (V) {
          console.log("[a2a] SSE stream ended (done)");
          break;
        }
        G += ge.decode(q, { stream: !0 });
        const H = G.split(`
`);
        G = H.pop() || "";
        for (const u of H)
          if (u.startsWith("data: "))
            try {
              const w = JSON.parse(u.slice(6));
              if (console.log("[a2a] SSE event:", w), w.done) {
                w.error && (a.textContent = `错误: ${w.error}`, a.style.borderColor = "#ff4d4f", a.style.background = "#fff1f0"), console.log("[a2a] SSE done signal received");
                return;
              }
              typeof w.response_text == "string" && w.response_text && (a.textContent = w.response_text);
            } catch (w) {
              console.warn("[a2a] SSE parse error:", w, "line:", u);
            }
      }
    } catch (k) {
      (k == null ? void 0 : k.name) !== "AbortError" && (console.error("[a2a] SSE subscription error:", k), a.textContent = `连接出错: ${(k == null ? void 0 : k.message) || k}`, a.style.borderColor = "#ff4d4f", a.style.background = "#fff1f0");
    }
  }
  function Lt() {
    console.log("[a2a] Initializing stream interceptor");
    function t(d) {
      if (d.nodeType !== Node.ELEMENT_NODE) return;
      const h = d, a = it(h);
      if (a && Ke.has(a)) return;
      const c = Dt(h);
      c && (console.log("[a2a] Marker detected in DOM, msgId:", a), a && Ke.add(a), ct(c));
    }
    new MutationObserver((d) => {
      for (const h of d) {
        for (const a of h.addedNodes)
          t(a);
        h.target.nodeType === Node.ELEMENT_NODE && t(h.target);
      }
    }).observe(document.body, {
      childList: !0,
      subtree: !0,
      characterData: !0,
      characterDataOldValue: !0
    });
    const o = setInterval(() => {
      const d = document.evaluate(
        "//text()[contains(., 'A2A_STREAM_START')]",
        document.body,
        null,
        XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
        null
      );
      for (let h = 0; h < d.snapshotLength; h++) {
        const c = d.snapshotItem(h).parentElement;
        if (c) {
          const l = it(c);
          if (l && Ke.has(l)) continue;
          console.log("[a2a] Marker found in periodic scan, msgId:", l), l && Ke.add(l), ct(c);
        }
      }
    }, 500);
    window.addEventListener("beforeunload", () => clearInterval(o));
    const i = document.evaluate(
      "//text()[contains(., 'A2A_STREAM_START')]",
      document.body,
      null,
      XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
      null
    );
    for (let d = 0; d < i.snapshotLength; d++) {
      const a = i.snapshotItem(d).parentElement;
      if (a) {
        const c = it(a);
        c && Ke.add(c), console.log("[a2a] Marker found in existing DOM, msgId:", c), ct(a);
      }
    }
  }
  (bt = (St = window.JotaDuo).registerToolRender) == null || bt.call(St, "cloudpaw", {
    proposal_choice: Ne,
    manage_prd: lt,
    a2a_call: Ot
  }), (kt = (At = window.JotaDuo).registerRoutes) == null || kt.call(At, "cloudpaw", [
    {
      path: "/a2a",
      component: Pt,
      label: "A2A",
      icon: "🔗",
      priority: 10
    }
  ]), Xt(), Gt(), Lt();
}
function Xt() {
  const e = "jotaduo-last-used-agent", P = "jotaduo-agent-storage", N = "cloudpaw-first-install", O = "cloud-orchestrator";
  if (localStorage.getItem(N)) return;
  localStorage.setItem(N, "true");
  function X() {
    localStorage.setItem(e, O);
    try {
      const Z = localStorage.getItem(P);
      if (Z) {
        const D = JSON.parse(Z);
        D.state = D.state || {}, D.state.selectedAgent = O, localStorage.setItem(P, JSON.stringify(D));
      } else
        localStorage.setItem(
          P,
          JSON.stringify({
            version: 0,
            state: {
              selectedAgent: O,
              agents: [],
              lastChatIdByAgent: {}
            }
          })
        );
    } catch {
    }
    try {
      const Z = sessionStorage.getItem(P);
      if (Z) {
        const D = JSON.parse(Z);
        D.state = D.state || {}, D.state.selectedAgent = O, sessionStorage.setItem(P, JSON.stringify(D));
      } else
        sessionStorage.setItem(
          P,
          JSON.stringify({
            version: 0,
            state: {
              selectedAgent: O,
              agents: [],
              lastChatIdByAgent: {}
            }
          })
        );
    } catch {
    }
  }
  X(), window.addEventListener(
    "beforeunload",
    () => {
      X();
    },
    { once: !0 }
  ), console.info(
    "[cloudpaw] Set default agent to cloud-orchestrator for first-time user"
  ), window.location.reload();
}
function Gt() {
  var re, g, L;
  const e = (g = (re = window.JotaDuo) == null ? void 0 : re.host) == null ? void 0 : g.React;
  if (!e) return;
  const P = (L = window.JotaDuo) == null ? void 0 : L.modules;
  if (!P) return;
  const N = P["Chat/OptionsPanel/defaultConfig"];
  if (!(N != null && N.configProvider)) {
    console.warn(
      "[cloudpaw] configProvider not found — skipping welcome/theme patch"
    );
    return;
  }
  const O = N.configProvider, X = O.getConfig.bind(O), Z = Kt(e), D = "https://gw.alicdn.com/imgextra/i2/O1CN01pyXzjQ1EL1PuZMlSd_!!6000000000334-2-tps-288-288.png", M = {
    zh: "CloudPaw 插件提示",
    en: "CloudPaw Plugin Tips",
    ja: "CloudPaw プラグインのヒント",
    ru: "Подсказки плагина CloudPaw"
  }, $e = {
    zh: `告诉 CloudPaw 你想做什么，它会自动帮你完成云资源管理、基础设施编排与应用创建上云等任务。
⚠️ 使用前请在左上角下拉框切换到「CloudPaw-Master」，否则功能无法正常使用！
对于复杂的长程任务，建议使用 /mission 命令启动 Mission Mode 来自动拆解和执行。`,
    en: `Tell CloudPaw what you want to do — it will automatically handle cloud resource management, infrastructure orchestration, and application deployment.
⚠️ Please switch to 'CloudPaw-Master' from the dropdown in the top-left corner before use — features won't work otherwise!
For complex, multi-step tasks, use /mission to start Mission Mode for automated decomposition and execution.`,
    ja: `CloudPaw にやりたいことを伝えるだけで、クラウドリソース管理、インフラ構成、アプリケーションのデプロイなどを自動で行います。
⚠️ 使用前に左上のドロップダウンから「CloudPaw-Master」に切り替えてください。切り替えないと機能が正常に動作しません！
複雑なタスクには /mission コマンドで Mission Mode を起動し、自動分解・実行できます。`,
    ru: `Расскажите CloudPaw, что вы хотите сделать — он автоматически выполнит управление облачными ресурсами, оркестрацию инфраструктуры и развёртывание приложений.
⚠️ Перед началом переключитесь на 'CloudPaw-Master' в выпадающем списке в левом верхнем углу — иначе функции не будут работать!
Для сложных задач используйте /mission для автоматической декомпозиции и выполнения.`
  }, F = {
    zh: [
      {
        label: "创建个人主页并部署到云端",
        value: "/mission 帮我创建一个个人主页并上线到云端。页面包含：个人介绍、技能展示、项目经历、联系方式，所有个人信息请先用占位符代替。风格简洁清爽，适配手机和电脑。请使用阿里云 ECS 部署。"
      },
      {
        label: "快速发布 API 服务到云端",
        value: "/mission 帮我把一个 API 服务快速发布到云端。我希望默认提供 /health 和 /hello 两个接口，并给我可直接调用的地址和示例请求，配置尽量简单清晰。"
      }
    ],
    en: [
      {
        label: "Create a personal homepage and deploy to the cloud",
        value: "/mission Help me create a personal homepage and deploy it to the cloud. The page should include: personal introduction, skills, project experience, and contact info — please use placeholders for all personal information. The style should be clean and minimal, responsive for mobile and desktop. Please deploy using Alibaba Cloud ECS."
      },
      {
        label: "Deploy an API service to the cloud",
        value: "/mission Help me quickly deploy an API service to the cloud. I want it to provide /health and /hello endpoints by default, and give me a callable URL with example requests. Keep the configuration as simple and clean as possible."
      }
    ]
  };
  function _() {
    const z = localStorage.getItem("language") || "";
    return z ? z.split("-")[0] : (navigator.language || "").split("-")[0] || "en";
  }
  function le({
    greeting: z,
    description: B,
    prompts: Q,
    onSubmit: j
  }) {
    const Ie = Array.isArray(Q) ? Q : [];
    return e.createElement(
      "section",
      { className: "cloudpaw-welcome-aura-panel" },
      e.createElement(
        "div",
        { className: "cloudpaw-welcome-aura-shell" },
        e.createElement(Z, {
          size: "sm",
          state: "thinking",
          color: "#4b8fce",
          colorShift: 0.22,
          className: "cloudpaw-welcome-aura-canvas"
        })
      ),
      e.createElement(
        "h2",
        { className: "cloudpaw-welcome-aura-title" },
        z
      ),
      B ? e.createElement(
        "p",
        { className: "cloudpaw-welcome-aura-description" },
        B
      ) : null,
      Ie.length ? e.createElement(
        "div",
        { className: "cloudpaw-welcome-aura-prompts" },
        Ie.map(
          (b) => e.createElement(
            "button",
            {
              key: b.value,
              type: "button",
              className: "cloudpaw-welcome-aura-prompt",
              onClick: () => j({ query: b.value })
            },
            e.createElement("span", null, b.label || b.value),
            e.createElement("span", { "aria-hidden": !0 }, "→")
          )
        )
      ) : null
    );
  }
  O.getGreeting = () => M[_()] || M.en, O.getDescription = () => $e[_()] || $e.en, O.getPrompts = () => F[_()] || F.en, O.getConfig = function(z) {
    var Q;
    const B = X(z);
    return {
      ...B,
      theme: {
        ...B.theme,
        leftHeader: {
          ...(Q = B.theme) == null ? void 0 : Q.leftHeader,
          title: "Work with CloudPaw"
        }
      },
      welcome: {
        ...B.welcome,
        avatar: D,
        render: le
      }
    };
  };
  const ne = document.getElementById("cloudpaw-welcome-style") || document.createElement("style");
  ne.id = "cloudpaw-welcome-style", ne.textContent = `
      [class*="chat-anywhere-welcome-default"] [class*="description"],
      [class*="message-list-welcome"] [class*="description"] {
        white-space: pre-line !important;
        text-align: center !important;
      }
      .cloudpaw-welcome-aura-panel {
        width: min(760px, 100%);
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
        color: var(--app-text, rgba(241, 245, 249, 0.82));
        text-align: center;
      }
      .cloudpaw-welcome-aura-shell {
        width: 76px;
        height: 76px;
        display: grid;
        place-items: center;
        border-radius: 50%;
        background:
          radial-gradient(circle at 50% 45%, rgba(75, 143, 206, 0.16), transparent 62%),
          var(--app-surface, rgba(21, 23, 25, 0.98));
        box-shadow:
          0 0 0 1px var(--app-border-subtle, rgba(226, 232, 240, 0.09)),
          0 18px 38px rgba(0, 0, 0, 0.22);
      }
      .cloudpaw-welcome-aura-canvas {
        filter: saturate(1.08);
      }
      .cloudpaw-welcome-aura-title {
        margin: 0;
        font-size: 15px;
        font-weight: 650;
        line-height: 1.4;
        color: var(--app-text-strong, rgba(248, 250, 252, 0.94));
      }
      .cloudpaw-welcome-aura-description {
        max-width: 740px;
        margin: 0;
        white-space: pre-line;
        font-size: 12px;
        line-height: 1.55;
        color: var(--app-text-muted, rgba(203, 213, 225, 0.68));
      }
      .cloudpaw-welcome-aura-prompts {
        width: min(360px, 100%);
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 6px;
      }
      .cloudpaw-welcome-aura-prompt {
        width: 100%;
        min-height: 38px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 8px 14px;
        border: 1px solid var(--app-border-subtle, rgba(226, 232, 240, 0.09));
        border-radius: 8px;
        background: var(--app-surface-subtle, rgba(32, 36, 42, 0.82));
        color: var(--app-text, rgba(241, 245, 249, 0.82));
        font: inherit;
        font-size: 13px;
        cursor: pointer;
        transition:
          background 0.18s ease,
          border-color 0.18s ease,
          color 0.18s ease,
          transform 0.18s ease;
      }
      .cloudpaw-welcome-aura-prompt:hover {
        border-color: var(--app-primary-border, rgba(75, 143, 206, 0.34));
        background: var(--app-surface-hover, rgba(38, 48, 58, 0.9));
        color: var(--app-text-strong, rgba(248, 250, 252, 0.94));
        transform: translateY(-1px);
      }
      .cloudpaw-welcome-aura-prompt:focus-visible {
        outline: none;
        box-shadow: var(--app-focus-ring, 0 0 0 2px rgba(75, 143, 206, 0.34));
      }
    `, ne.parentNode || document.head.appendChild(ne), console.info("[cloudpaw] Patched welcome config & theme via configProvider");
}
Yt();
