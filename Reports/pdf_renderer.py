from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
    Spacer, PageBreak, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import black, red, lightgrey
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

import matplotlib.pyplot as plt
import networkx as nx
import hashlib
import os
import logging

import re

from reportlab.platypus import Paragraph

def cell(text, style="S"):
    """
    Wrap table cell content safely.
    """
    if text is None:
        text = "N/A"
    return Paragraph(str(text), styles[style])

def normalize_list(v):
    """
    Normalize metadata fields like emails / pgp_keys.
    Fixes cases where JSON is parsed as char arrays.
    """
    if not v:
        return []

    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]

    if isinstance(v, str):
        return [v.strip()]

    return []


def format_identity_field(emails, pgp_keys):
    """
    Produce clean printable string for Emails / PGP column.
    """
    email_list = normalize_list(emails)
    pgp_list = normalize_list(pgp_keys)

    out = []
    if email_list:
        out.append("Emails: " + ", ".join(email_list))
    if pgp_list:
        out.append("PGP: " + ", ".join(pgp_list))

    return " | ".join(out) if out else "N/A"


def cover_page(elements, logo_path, title, subtitle_lines, analyst):
    """
    Build a clean forensic cover page.
    """

    # Push content down slightly
    # elements.append(Spacer(1, 40))

    # -------- LOGO (COVER – BIG BUT SAFE) --------
    # Lift content slightly
    elements.append(Spacer(1, 20))

    if logo_path and os.path.exists(logo_path):
        img = Image(logo_path)

        max_width = A4[0] - 40 * mm
        max_height = A4[1] * 0.48   # reduced height

        img._restrictSize(max_width, max_height)
        img.hAlign = "CENTER"

        elements.append(img)

    elements.append(Spacer(1, 22))


    # -------- TITLE --------
    elements.append(Paragraph(
        title,
        ParagraphStyle(
            "COVER_TITLE",
            fontName="Times-Bold",
            fontSize=22,
            leading=26,
            alignment=1,  # CENTER
            spaceAfter=14
        )
    ))

    # -------- SUB DETAILS --------
    for line in subtitle_lines:
        elements.append(Paragraph(
            line,
            ParagraphStyle(
                "COVER_SUB",
                fontName="Times-Roman",
                fontSize=12,
                alignment=1,
                spaceAfter=6
            )
        ))

    elements.append(Spacer(1, 40))

    # -------- ANALYST --------
    elements.append(Paragraph(
        f"Analyst: <b>{analyst}</b>",
        ParagraphStyle(
            "COVER_ANALYST",
            fontName="Times-Roman",
            fontSize=11,
            alignment=1,
            spaceAfter=10
        )
    ))

    elements.append(PageBreak())

def add_section(elements, title, content_blocks):
    """
    Add a section only if content exists.
    Prevents blank pages.
    """
    if not content_blocks:
        return

    elements.append(Paragraph(title, styles["H"]))
    for block in content_blocks:
        elements.append(block)

    elements.append(PageBreak())




# =====================================================
# LOGGING
# =====================================================
log = logging.getLogger("pdf_renderer")

# =====================================================
# STYLES
# =====================================================
styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    name="TITLE",
    fontName="Times-Bold",
    fontSize=18,
    spaceAfter=16
))

styles.add(ParagraphStyle(
    name="H",
    fontName="Times-Bold",
    fontSize=14,
    spaceBefore=14,
    spaceAfter=8
))

styles.add(ParagraphStyle(
    name="B",
    fontName="Times-Roman",
    fontSize=11,
    spaceAfter=6
))

styles.add(ParagraphStyle(
    name="S",
    fontName="Times-Roman",
    fontSize=9,
    spaceAfter=4
))

styles.add(ParagraphStyle(
    name="MONO",
    fontName="Courier",
    fontSize=8,
    wordWrap="CJK"
))

styles.add(ParagraphStyle(
    name="R",
    fontName="Times-Bold",
    fontSize=11,
    textColor=red
))

# =====================================================
# HEADER / FOOTER
# =====================================================
def watermark(c):
    c.saveState()
    c.setFont("Times-Bold", 48)
    c.setFillGray(0.92)
    c.translate(300, 400)
    c.rotate(45)
    c.drawCentredString(0, 0, "CONFIDENTIAL")
    c.restoreState()


def header_footer(c, doc, logo_path, sha256):
    try:
        if logo_path and os.path.exists(logo_path):
            c.drawImage(
                logo_path,
                20 * mm,
                A4[1] - 24 * mm,
                14 * mm,   # smaller width
                14 * mm,   # smaller height
                preserveAspectRatio=True,
                mask="auto"
            )

    except Exception as e:
        log.error(f"Logo error: {e}")

    c.setFont("Times-Roman", 8)
    c.drawString(20 * mm, 15 * mm, "SHA-256:")
    c.drawString(20 * mm, 11 * mm, sha256[:64])
    c.drawString(20 * mm, 7 * mm, sha256[64:])
    c.drawRightString(A4[0] - 20 * mm, 10 * mm, f"Page {doc.page}")

    watermark(c)

# =====================================================
# HELPERS
# =====================================================
def _safe(v):
    return v if v else "N/A"


def make_table(data, col_widths):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, black),
        ("BACKGROUND", (0,0), (-1,0), lightgrey),
        ("FONT", (0,0), (-1,0), "Times-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    return t


# =====================================================
# BTC GRAPH
# =====================================================
def draw_btc_transaction_graph(edges, subject, output_path):
    log.info(f"Generating BTC graph → {output_path}")

    G = nx.DiGraph()

    for e in edges:
        fan_in = e.get("fan_in") or 0
        fan_out = e.get("fan_out") or 0
        is_mixer = fan_in >= 10 or fan_out >= 10

        G.add_edge(
            e["from_address"],
            e["to_address"],
            weight=e.get("amount", 0),
            mixer=is_mixer
        )

    if not G.nodes:
        log.warning("BTC graph skipped (no nodes)")
        return None

    pos = nx.spring_layout(G, seed=42, k=0.9)

    node_colors = []
    for n in G.nodes:
        if n == subject:
            node_colors.append("green")
        else:
            node_colors.append(
                "red" if any(G[u][v]["mixer"] for u, v in G.edges(n)) else "gray"
            )

    plt.figure(figsize=(7, 6))
    nx.draw(
        G, pos,
        node_color=node_colors,
        node_size=280,
        width=0.6,
        arrowsize=10,
        with_labels=False
    )
    plt.title("Bitcoin Transaction Network")
    plt.tight_layout()
    plt.savefig(output_path, dpi=220)
    plt.close()

    with open(output_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

# =====================================================
# SITE DOSSIER
# =====================================================
def render_site_dossier_pdf(report, output_path, logo_path):
    log.info("Rendering SITE_DOSSIER PDF")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=35*mm,
        bottomMargin=25*mm
    )

    e = []
    es = report["executive_summary"]
    integ = report["integrity"]

    # ======================================================
    # COVER
    # ======================================================
    cover_page(
        e,
        logo_path='assets/cover_logo.png',
        title="SITE DOSSIER REPORT",
        subtitle_lines=[
            f"Onion URL: {es['url']}",
            f"Status: {es['status']} | Category: {es['category']}",
            f"First Seen: {_safe(es['first_seen'])}",
            f"Last Seen: {_safe(es['last_seen'])}",
        ],
        analyst="Abhishek P Nair"
    )

    
    e.append(Paragraph("Site Overview", styles["H"]))

    if es.get("site_title"):
        e.append(Paragraph(es["site_title"], styles["TITLE"]))

    e.append(Paragraph(
        f"Status: {es['status']} | Category: {es['category']}",
        styles["B"]
    ))


    e.append(PageBreak())

    # ======================================================
    # CRAWLED PAGES
    # ======================================================
    e.append(Paragraph("Crawled Pages", styles["H"]))

    rows = [[
        cell("URL", "B"),
        cell("HTML Hash", "B"),
        cell("Crawl Date", "B")
    ]]

    for p in report["body"]["pages"]:
        rows.append([
            cell(p["url"]),
            cell(p["html_hash"], "MONO"),
            cell(_safe(p["crawl_date"]))
        ])

    e.append(make_table(rows, [75*mm, 55*mm, 35*mm]))
    e.append(PageBreak())

    # ======================================================
    # METADATA EXTRACTION
    # ======================================================
    e.append(Paragraph("Extracted Metadata", styles["H"]))

    

    meta_rows = [[
        cell("Page ID", "B"),
        cell("Title", "B"),
        cell("Language", "B"),
        cell("Emails / PGP", "B")
    ]]

    for p in report["body"]["pages"]:
        m = p.get("metadata")
        if not m:
            continue

        meta_rows.append([
            cell(p["page_id"][:12], "MONO"),
            cell(m.get("title")),
            cell(m.get("language")),
            cell(
                format_identity_field(
                    m.get("emails"),
                    m.get("pgp_keys")
                )
            )
        ])

    

    e.append(make_table(meta_rows, [40*mm, 50*mm, 25*mm, 50*mm]))
    e.append(PageBreak())

    # ======================================================
    # BITCOIN INFRASTRUCTURE
    # ======================================================
    e.append(Paragraph("Bitcoin Infrastructure", styles["H"]))

    btc_rows = [[
        cell("Address", "B"),
        cell("Page ID", "B"),
        cell("Valid", "B"),
        cell("Detected At", "B")
    ]]

    for b in report["artifacts"]["bitcoin_addresses"]:
        btc_rows.append([
            cell(b["artifact_value"], "MONO"),
            cell(b["source_page"], "MONO"),
            cell("Yes" if b["valid"] else "No"),
            cell(_safe(b["first_seen"]))
        ])

    if len(btc_rows) > 1:
        e.append(make_table(btc_rows, [65*mm, 40*mm, 20*mm, 35*mm]))
    else:
        e.append(Paragraph("No Bitcoin addresses detected.", styles["S"]))

    e.append(PageBreak())

    # ======================================================
    # VENDOR ASSOCIATIONS
    # ======================================================
    e.append(Paragraph("Vendor Associations", styles["H"]))

    vendor_rows = [[
        cell("Vendor ID", "B"),
        cell("Artifact Type", "B"),
        cell("Value", "B"),
        cell("Confidence", "B"),
        cell("Risk Score", "B")
    ]]

    for v in report["artifacts"]["vendor_artifacts"]:
        vendor_rows.append([
            cell(
            f"{v.get('vendor_name','Unknown')} ({v['vendor_id'][:8]})"
            ),
            cell(v["artifact_type"]),
            cell(v["artifact_value"], "MONO"),
            cell(str(v["confidence"])),
            cell(str(v.get("risk_score", "N/A")))
        ])

    if len(vendor_rows) > 1:
        e.append(make_table(vendor_rows, [40*mm, 30*mm, 45*mm, 20*mm, 25*mm]))
    else:
        e.append(Paragraph("No vendor artifacts associated.", styles["S"]))

    e.append(PageBreak())

    # ======================================================
    # INTEGRITY & VERIFICATION
    # ======================================================
    e.append(Paragraph("Integrity & Verification", styles["H"]))
    e.append(Paragraph("JSON Hash:", styles["B"]))
    e.append(Paragraph(integ["json_hash"], styles["MONO"]))
    e.append(Paragraph("Signature:", styles["B"]))
    e.append(Paragraph(integ["signature"], styles["MONO"]))
    e.append(Paragraph(f"Public Key ID: {integ['public_key_id']}", styles["S"]))
    e.append(Paragraph(f"Signed At: {integ['signed_at']}", styles["S"]))

    # ======================================================
    # BUILD
    # ======================================================
    doc.build(
        e,
        onFirstPage=lambda c, d: header_footer(c, d, logo_path, integ["json_hash"]),
        onLaterPages=lambda c, d: header_footer(c, d, logo_path, integ["json_hash"])
    )

    log.info("SITE_DOSSIER PDF render completed")
    return output_path


# =====================================================
# BTC ADDRESS REPORT
# =====================================================
def render_btc_address_pdf(report, output_path, logo_path):
    log.info("Rendering BTC_ADDRESS_REPORT")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=35*mm,
        bottomMargin=25*mm
    )

    e = []
    es = report["executive_summary"]
    integ = report["integrity"]

    # --------------------------------------------------
    # COVER
    # --------------------------------------------------
    cover_page(
        e,
        logo_path='assets/cover_logo.png',
        title="BITCOIN ADDRESS<br/>INTELLIGENCE REPORT",
        subtitle_lines=[
            f"BTC Address: {es['btc_address']}",
            f"Checksum Valid: {'Yes' if es['checksum_valid'] else 'No'}",
            f"First Seen: {_safe(es['first_seen'])}"
        ],
        analyst="Abhishek P Nair"
    )


    risk_blocks = [
        Paragraph(f"⚠ {rf}", styles["R"])
        for rf in es.get("risk_flags", [])
    ]

    
    add_section(
        e,
        title="Risk Summary",
        content_blocks=risk_blocks
    )


    # --------------------------------------------------
    # LINKED SITES
    # --------------------------------------------------
    e.append(Paragraph("Linked Onion Sites", styles["H"]))

    site_rows = [[
        cell("Site ID", "B"),
        cell("URL", "B"),
        cell("Category", "B"),
        cell("First Seen", "B"),
        cell("Last Seen", "B")
    ]]

    for s in report["evidence"]["linked_sites"]:
        site_rows.append([
            cell(s["site_id"][:12], "MONO"),
            cell(s["url"]),
            cell(s.get("keyword")),
            cell(_safe(s["first_seen"])),
            cell(_safe(s["last_seen"]))
        ])

    if len(site_rows) > 1:
        e.append(make_table(site_rows, [35*mm, 60*mm, 30*mm, 30*mm, 30*mm]))
    else:
        e.append(Paragraph("No linked sites detected.", styles["S"]))

    e.append(PageBreak())

    # --------------------------------------------------
    # TRANSACTION HISTORY
    # --------------------------------------------------
    e.append(Paragraph("Transaction Evidence", styles["H"]))

    tx_rows = [[
        cell("Tx ID", "B"),
        cell("Direction", "B"),
        cell("Amount (BTC)", "B"),
        cell("Fan-In", "B"),
        cell("Fan-Out", "B"),
        cell("Timestamp", "B")
    ]]

    for t in report["evidence"]["transactions"]:
        tx_rows.append([
            cell(t["tx_id"][:12], "MONO"),
            cell(t["direction"]),
            cell(str(t["amount"])),
            cell(str(t["fan_in"])),
            cell(str(t["fan_out"])),
            cell(_safe(t["timestamp"]))
        ])

    if len(tx_rows) > 1:
        e.append(make_table(tx_rows, [30*mm, 25*mm, 25*mm, 20*mm, 20*mm, 40*mm]))
    else:
        e.append(Paragraph("No transactions available.", styles["S"]))

    e.append(PageBreak())

    # --------------------------------------------------
    # VENDOR ATTRIBUTION
    # --------------------------------------------------
    e.append(Paragraph("Vendor Attribution", styles["H"]))

    vend_rows = [[
        cell("Vendor ID", "B"),
        cell("Risk Score", "B"),
        cell("First Seen", "B"),
        cell("Last Seen", "B")
    ]]

    for v in report["evidence"]["vendors"]:
        vend_rows.append([
            cell(
                f"{v.get('vendor_name','Unknown')} ({v['vendor_id'][:8]})"
            ),
            cell(str(v["risk_score"])),
            cell(_safe(v["first_seen"])),
            cell(_safe(v["last_seen"]))
        ])

    if len(vend_rows) > 1:
        e.append(make_table(vend_rows, [45*mm, 25*mm, 40*mm, 40*mm]))
    else:
        e.append(Paragraph("No vendor attribution detected.", styles["S"]))

    e.append(PageBreak())

    # --------------------------------------------------
    # TRANSACTION GRAPH
    # --------------------------------------------------
    graph_blocks = []

    graph = report["report_metadata"].get("graph_artifacts", {}).get("transaction_graph")
    if graph and graph.get("file") and os.path.exists(graph["file"]):
        graph_blocks.append(Spacer(1, 10))
        graph_blocks.append(
            Image(
                graph["file"],
                width=160 * mm,
                height=120 * mm
            )
        )
        graph_blocks.append(Spacer(1, 6))
        graph_blocks.append(
            Paragraph(f"Graph SHA-256: {graph['sha256']}", styles["MONO"])
        )

    add_section(
        e,  # or elements — same function
        title="Transaction Network Graph",
        content_blocks=graph_blocks
    )


    # --------------------------------------------------
    # INTEGRITY
    # --------------------------------------------------
    e.append(Paragraph("Integrity & Verification", styles["H"]))
    e.append(Paragraph("JSON Hash:", styles["B"]))
    e.append(Paragraph(integ["json_hash"], styles["MONO"]))
    e.append(Paragraph("Signature:", styles["B"]))
    e.append(Paragraph(integ["signature"], styles["MONO"]))
    e.append(Paragraph(f"Public Key ID: {integ['public_key_id']}", styles["S"]))
    e.append(Paragraph(f"Signed At: {integ['signed_at']}", styles["S"]))

    doc.build(
        e,
        onFirstPage=lambda c, d: header_footer(c, d, logo_path, integ["json_hash"]),
        onLaterPages=lambda c, d: header_footer(c, d, logo_path, integ["json_hash"])
    )

    return output_path


# =====================================================
# VENDOR PROFILE
# =====================================================
def render_vendor_profile_pdf(report, output_path, logo_path):
    log.info("Rendering VENDOR_PROFILE PDF")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=35*mm,
        bottomMargin=25*mm
    )

    e = []
    es = report["executive_summary"]
    integ = report["integrity"]

    # --------------------------------------------------
    # COVER
    # --------------------------------------------------
    cover_page(
        e,
        logo_path='assets/cover_logo.png',
        title = "VENDOR PROFILE<br/>INTELLIGENCE REPORT",
        subtitle_lines=[
            f"Vendor: {es.get('vendor_name','Unknown')}",
            f"Vendor ID: {es['vendor_id']}",
            f"Risk Score: {es['risk_score']}"
        ],
        analyst="Abhishek P Nair"
    )


    risk_blocks = [
        Paragraph(f"⚠ {rf}", styles["R"])
        for rf in es.get("risk_flags", [])
    ]

    add_section(
        e,
        title="Risk Indicators",
        content_blocks=risk_blocks
    )


    # --------------------------------------------------
    # ASSOCIATED SITES
    # --------------------------------------------------
    e.append(Paragraph("Associated Onion Sites", styles["H"]))

    site_rows = [[
        cell("Site ID", "B"),
        cell("URL", "B"),
        cell("Category", "B"),
        cell("First Seen", "B"),
        cell("Last Seen", "B")
    ]]

    for s in report["associations"]["onion_sites"]:
        site_rows.append([
            cell(s["site_id"][:12], "MONO"),
            cell(s["url"]),
            cell(s.get("keyword")),
            cell(_safe(s["first_seen"])),
            cell(_safe(s["last_seen"]))
        ])

    if len(site_rows) > 1:
        e.append(make_table(site_rows, [35*mm, 60*mm, 30*mm, 30*mm, 30*mm]))
    else:
        e.append(Paragraph("No associated sites detected.", styles["S"]))

    e.append(PageBreak())

    # --------------------------------------------------
    # VENDOR ARTIFACTS
    # --------------------------------------------------
    e.append(Paragraph("Vendor Artifacts", styles["H"]))

    art_rows = [[
        cell("Type", "B"),
        cell("Value", "B"),
        cell("Confidence", "B")
    ]]

    for a in report["artifacts"]["identities"]:
        art_rows.append([
            cell(a["artifact_type"]),
            cell(a["artifact_value"], "MONO"),
            cell(str(a["confidence"]))
        ])

    e.append(make_table(art_rows, [40*mm, 90*mm, 30*mm]))
    e.append(PageBreak())

    # --------------------------------------------------
    # BTC ADDRESSES
    # --------------------------------------------------
    e.append(Paragraph("Bitcoin Addresses", styles["H"]))

    btc_rows = [[
        cell("Address", "B"),
        cell("Valid", "B"),
        cell("Detected At", "B")
    ]]

    for b in report["artifacts"]["bitcoin_addresses"]:
        btc_rows.append([
            cell(b["address"], "MONO"),
            cell("Yes" if b["valid"] else "No"),
            cell(_safe(b["detected_at"]))
        ])

    if len(btc_rows) > 1:
        e.append(make_table(btc_rows, [90*mm, 30*mm, 40*mm]))
    else:
        e.append(Paragraph("No BTC addresses linked.", styles["S"]))

    e.append(PageBreak())

    # --------------------------------------------------
    # BTC TRANSACTION GRAPH
    # --------------------------------------------------
    edges = report["graph"]["btc_transaction_edges"]
    if edges:
        img = output_path.replace(".pdf", "_btc_graph.png")
        draw_btc_transaction_graph(edges, None, img)
        e.append(Paragraph("Bitcoin Transaction Network", styles["H"]))
        e.append(Image(img, width=160*mm, height=120*mm))
        e.append(PageBreak())

    # --------------------------------------------------
    # INTEGRITY
    # --------------------------------------------------
    e.append(Paragraph("Integrity & Verification", styles["H"]))
    e.append(Paragraph("JSON Hash:", styles["B"]))
    e.append(Paragraph(integ["json_hash"], styles["MONO"]))
    e.append(Paragraph("Signature:", styles["B"]))
    e.append(Paragraph(integ["signature"], styles["MONO"]))
    e.append(Paragraph(f"Public Key ID: {integ['public_key_id']}", styles["S"]))
    e.append(Paragraph(f"Signed At: {integ['signed_at']}", styles["S"]))

    doc.build(
        e,
        onFirstPage=lambda c, d: header_footer(c, d, logo_path, integ["json_hash"]),
        onLaterPages=lambda c, d: header_footer(c, d, logo_path, integ["json_hash"])
    )

    return output_path


# =====================================================
# ALL SITES MEGA REPORT
# =====================================================
def render_all_sites_pdf(report, output_path, logo_path):
    log.info("Rendering ALL_SITES PDF")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=35*mm,
        bottomMargin=25*mm
    )

    e = []
    es = report["executive_summary"]
    integ = report["integrity"]

    # ======================================================
    # COVER
    # ======================================================
    cover_page(
        e,
        logo_path='assets/cover_logo.png',
        title="ALL SITES – MEGA<br/>INTELLIGENCE REPORT",
        subtitle_lines=[
            f"Total Sites: {es['total_sites']}",
            f"Total Vendors: {es['total_vendors']}",
            f"Total BTC Addresses: {es['total_btc_addresses']}"
        ],
        analyst="Abhishek P Nair"
    )


    risk_blocks = [
        Paragraph(f"⚠ {rf}", styles["R"])
        for rf in es.get("risk_flags", [])
    ]

    add_section(
        e,
        title="Risk Indicators",
        content_blocks=risk_blocks
    )


    # ======================================================
    # CATEGORY DISTRIBUTION
    # ======================================================
    e.append(Paragraph("Category Distribution", styles["H"]))

    rows = [[cell("Category", "B"), cell("Sites", "B")]]
    for c in report["category_intel"]:
        rows.append([cell(c["category"]), cell(str(c["count"]))])

    e.append(make_table(rows, [90*mm, 40*mm]))
    e.append(PageBreak())

    # ======================================================
    # SITE ECOSYSTEM
    # ======================================================
    e.append(Paragraph("Site Ecosystem Overview", styles["H"]))

    rows = [[
        cell("Site ID", "B"),
        cell("Category", "B"),
        cell("Vendors", "B"),
        cell("BTC", "B"),
        cell("Status", "B")
    ]]

    for s in report["entities"]["sites"]:
        rows.append([
            cell(s["site_id"][:12], "MONO"),
            cell(s["keyword"]),
            cell(str(s.get("vendor_count", 0))),
            cell(str(s.get("btc_count", 0))),
            cell(s["current_status"])
        ])

    e.append(make_table(rows, [40*mm, 35*mm, 25*mm, 20*mm, 30*mm]))
    e.append(PageBreak())

    # ======================================================
    # VENDOR ECOSYSTEM
    # ======================================================
    e.append(Paragraph("Vendor Ecosystem Overview", styles["H"]))

    rows = [[
        cell("Vendor ID", "B"),
        cell("Risk", "B"),
        cell("Sites", "B"),
        cell("BTC", "B")
    ]]

    for v in report["entities"]["vendors"]:
        rows.append([
            cell(
                f"{v.get('vendor_name','Unknown')} ({v['vendor_id'][:8]})"
            ),
            cell(str(v["risk_score"])),
            cell(str(v.get("site_count", 0))),
            cell(str(v.get("btc_count", 0)))
        ])

    e.append(make_table(rows, [45*mm, 30*mm, 30*mm, 30*mm]))
    e.append(PageBreak())

    # ======================================================
    # INTEGRITY & VERIFICATION
    # ======================================================
    e.append(Paragraph("Integrity & Verification", styles["H"]))
    e.append(Paragraph("JSON Hash:", styles["B"]))
    e.append(Paragraph(integ["json_hash"], styles["MONO"]))
    e.append(Spacer(1, 6))
    e.append(Paragraph("Signature:", styles["B"]))
    e.append(Paragraph(integ["signature"], styles["MONO"]))
    e.append(Spacer(1, 6))

    e.append(Paragraph(
        f"Public Key ID: {integ['public_key_id']}",
        styles["S"]
    ))

    e.append(Paragraph(
        f"Signed At: {integ['signed_at']}",
        styles["S"]
    ))


    doc.build(
        e,
        onFirstPage=lambda c,d: header_footer(c,d,logo_path,integ["json_hash"]),
        onLaterPages=lambda c,d: header_footer(c,d,logo_path,integ["json_hash"])
    )

    return output_path


# --------------------------------------------------
# CATEGORY INTEL PDF (CLEAN & ALIGNED)
# --------------------------------------------------
def render_category_intel_pdf(report, output_path, logo_path):
    log.info(f"Rendering CATEGORY_INTEL PDF → {output_path}")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=35 * mm,
        bottomMargin=25 * mm
    )

    elements = []
    es = report["executive_summary"]
    meta = report["report_metadata"]
    integ = report["integrity"]

    # ---------------- COVER ----------------
    cover_page(
        elements,
        logo_path='assets/cover_logo.png',
        title="CATEGORY INTELLIGENCE REPORT",
        subtitle_lines=[
            f"Category: {es['category']}",
            f"Sites: {es['site_count']} | Vendors: {es['vendor_count']}"
        ],
        analyst="Abhishek P Nair"
    )


    risk_blocks = [
        Paragraph(f"⚠ {rf}", styles["R"])
        for rf in es.get("risk_flags", [])
    ]

    add_section(
        elements,
        title="Risk Indicators",
        content_blocks=risk_blocks
    )


    # ---------------- SITES ----------------
    elements.append(Paragraph("Sites in Category", styles["H"]))

    site_rows = [[
        cell("Site ID", "B"),
        cell("URL", "B"),
        cell("Status", "B"),
        cell("First Seen", "B"),
        cell("Last Seen", "B")
    ]]

    for s in report["sites"]:
        site_rows.append([
            cell(s["site_id"]),
            cell(s["url"]),
            cell(s["current_status"]),
            cell(_safe(s["first_seen"])),
            cell(_safe(s["last_seen"]))
        ])


    elements.append(make_table(site_rows, [35*mm, 55*mm, 25*mm, 30*mm, 30*mm]))
    elements.append(PageBreak())

    # ---------------- VENDORS ----------------
    elements.append(Paragraph("Associated Vendors", styles["H"]))

    vend_rows = [[
        cell("Vendor", "B"),
        cell("Risk", "B"),
        cell("First Seen", "B"),
        cell("Last Seen", "B")
    ]]

    for v in report["vendors"]:
        vend_rows.append([
            cell(f"{v.get('vendor_name','Unknown')} ({v['vendor_id'][:8]})"),
            cell(str(v["risk_score"])),
            cell(_safe(v["first_seen"])),
            cell(_safe(v["last_seen"]))
        ])


    elements.append(make_table(vend_rows, [40*mm, 25*mm, 40*mm, 40*mm]))
    elements.append(PageBreak())

    # ---------------- BTC ----------------
    elements.append(Paragraph("Bitcoin Infrastructure", styles["H"]))

    btc_rows = [[
        cell("Address", "B"),
        cell("Site ID", "B"),
        cell("Valid", "B"),
        cell("Detected At", "B")
    ]]

    for b in report["bitcoin_addresses"]:
        btc_rows.append([
            cell(b["address"], "MONO"),
            cell(b["site_id"]),
            cell("Yes" if b["valid"] else "No"),
            cell(_safe(b["detected_at"]))
        ])


    elements.append(make_table(btc_rows, [55*mm, 25*mm, 20*mm, 45*mm]))
    elements.append(PageBreak())

    # ---------------- GRAPH ----------------
    graph_blocks = []

    graph = meta.get("graph_artifacts", {}).get("btc_transaction_graph")
    if graph and graph.get("file") and os.path.exists(graph["file"]):
        graph_blocks.append(Spacer(1, 10))
        graph_blocks.append(
            KeepTogether(
                Image(
                    graph["file"],
                    width=160 * mm,
                    height=120 * mm
                )
            )
        )
        graph_blocks.append(Spacer(1, 6))
        graph_blocks.append(
            Paragraph(f"Graph SHA-256: {graph['sha256']}", styles["MONO"])
        )

    add_section(
        elements,
        title="Bitcoin Transaction Network",
        content_blocks=graph_blocks
    )


    # ---------------- INTEGRITY ----------------
    elements.append(Paragraph("Integrity & Verification", styles["H"]))
    elements.append(Paragraph(f"JSON Hash:", styles["B"]))
    elements.append(Paragraph(integ["json_hash"], styles["MONO"]))
    elements.append(Paragraph("Signature:", styles["B"]))
    elements.append(Paragraph(integ["signature"], styles["MONO"]))
    elements.append(Paragraph(f"Public Key ID: {integ['public_key_id']}", styles["S"]))
    elements.append(Paragraph(f"Signed At: {integ['signed_at']}", styles["S"]))

    doc.build(
        elements,
        onFirstPage=lambda c, d: header_footer(c, d, logo_path, integ["json_hash"]),
        onLaterPages=lambda c, d: header_footer(c, d, logo_path, integ["json_hash"])
    )

    log.info("CATEGORY_INTEL PDF render completed")
    return output_path
