import io
from datetime import datetime

def generate_order_text(orders, supplier_name="Supplier"):
    """
    Generates a clean text block for Email or WhatsApp.
    """
    header = f"""
🥐 *ARTISAN CRUMB - PURCHASE ORDER*
📅 Date: {datetime.now().strftime('%Y-%m-%d')}
🏭 Supplier: {supplier_name}

*PLEASE SUPPLY THE FOLLOWING:*
----------------------------------------
"""
    total_cost = 0
    body = ""
    
    for item in orders:
        line = f"• {item['name']}: {item['recommended_order']} {item['unit']} (Est: ${item['estimated_cost']})\n"
        body += line
        total_cost += item['estimated_cost']
        
    footer = f"""
----------------------------------------
💰 *TOTAL ESTIMATED: ${total_cost:.2f}*
📦 *Delivery Note:* Please deliver by {datetime.now().strftime('%A')} morning.
🙏 Thanks, Artisan Crumb Team.
    """
    
    return header + body + footer

def generate_pdf_bytes(orders, supplier_name="Supplier"):
    """
    Generates a simple PDF invoice for download.
    Uses built-in reportlab if available, else fallback to text.
    """
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        
        pdf.cell(0, 10, f"Purchase Order - Artisan Crumb", ln=True, align="C")
        pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')} | Supplier: {supplier_name}", ln=True, align="L")
        pdf.ln(10)
        
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(100, 10, "Item", border=1)
        pdf.cell(40, 10, "Qty", border=1)
        pdf.cell(40, 10, "Est. Cost", border=1, ln=True)
        pdf.set_font("Helvetica", size=12)
        
        total = 0
        for item in orders:
            pdf.cell(100, 10, item['name'], border=1)
            pdf.cell(40, 10, f"{item['recommended_order']} {item['unit']}", border=1)
            pdf.cell(40, 10, f"${item['estimated_cost']:.2f}", border=1, ln=True)
            total += item['estimated_cost']
            
        pdf.ln(10)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, f"Total Estimated Cost: ${total:.2f}", ln=True)
        
        return pdf.output(dest="S").encode("latin-1")
    except ImportError:
        # Fallback if fpdf not installed
        return None