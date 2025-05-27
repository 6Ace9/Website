from flask import Flask, request, render_template, redirect, url_for, jsonify, send_file
import os, json, time
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'C:\\Users\\6Ace9\\OneDrive\\Desktop\\Water Spider\\static\\images'
PARTS_FILE = 'parts.json'
BUILDS_FILE = 'builds.json'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def load_parts():
    if not os.path.exists(PARTS_FILE):
        return {}
    with open(PARTS_FILE, 'r') as f:
        return json.load(f)

def save_parts(parts):
    with open(PARTS_FILE, 'w') as f:
        json.dump(parts, f, indent=2)

def load_builds():
    if not os.path.exists(BUILDS_FILE):
        return {}
    with open(BUILDS_FILE, 'r') as f:
        return json.load(f)

def save_builds(builds):
    with open(BUILDS_FILE, 'w') as f:
        json.dump(builds, f, indent=2)

@app.route('/')
def HOME():
    return render_template('HOME.html')

@app.route('/Inventory')
def Inventory():
    parts = load_parts()
    return render_template('Inventory.html', parts=parts)

@app.route('/Inventory.html')
def redirect_Inventory():
    return redirect(url_for('Inventory'))

@app.route('/Builds')
def Builds():
    parts = load_parts()
    builds = load_builds()
    # Group builds by name
    grouped_builds = {}
    for build_id, build in builds.items():
        build_name = build['name']
        if build_name not in grouped_builds:
            grouped_builds[build_name] = []
        grouped_builds[build_name].append({
            'build_id': build_id,
            'parts': build['parts']
        })
    return render_template('Builds.html', parts=parts, grouped_builds=grouped_builds)

@app.route('/Builds.html')
def redirect_Builds():
    return redirect(url_for('Builds'))

@app.route('/Map')
def Map():
    return render_template('Map.html')

@app.route('/Map.html')
def redirect_Map():
    return redirect(url_for('Map'))

@app.route('/add_part', methods=['POST'])
def add_part():
    data = request.form
    parts = load_parts()
    pn = data['part_number']
    parts[pn] = {
        'description': data['description'],
        'location': data['location'],
        'length': data['length'],
        'width': data['width'],
        'comments': data['comments'],
        'image_path': data['image_path'],  # Store relative path (e.g., /static/images/filename.jpg)
    }
    save_parts(parts)
    return redirect(url_for('Inventory'))

@app.route('/delete_part/<part_number>')
def delete_part(part_number):
    parts = load_parts()
    if part_number in parts:
        del parts[part_number]
        save_parts(parts)
    # Remove part from all builds
    builds = load_builds()
    for build in builds.values():
        if part_number in build['parts']:
            build['parts'].remove(part_number)
    save_builds(builds)
    return redirect(url_for('Builds'))

@app.route('/upload_image', methods=['POST'])
def upload_image():
    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        # Return relative path for portability
        relative_path = os.path.join('/static/images', filename).replace('\\', '/')
        return jsonify({'image_path': relative_path})
    return jsonify({'error': 'No file uploaded'}), 400

@app.route('/upload_map', methods=['POST'])
def upload_map():
    file = request.files['map']
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], "Middle Earth.jpg")
        file.save(filepath)
        return redirect(url_for('Map'))
    return "No file selected", 400

@app.route('/search_part/<part_number>')
def search_part(part_number):
    parts = load_parts()
    part = parts.get(part_number)
    if part:
        return jsonify(part)
    return jsonify({'error': 'Part not found'}), 404

@app.route('/create_build', methods=['POST'])
def create_build():
    data = request.form
    build_name = data['build_name']
    selected_parts = request.form.getlist('parts')  # Get list of selected parts
    builds = load_builds()
    build_id = f"Build{len(builds) + 1}"
    builds[build_id] = {
        'name': build_name,
        'parts': selected_parts
    }
    save_builds(builds)
    return redirect(url_for('Builds'))

@app.route('/delete_build/<build_id>')
def delete_build(build_id):
    builds = load_builds()
    if build_id in builds:
        del builds[build_id]
        save_builds(builds)
    return redirect(url_for('Builds'))

@app.route('/export_pdf', methods=['GET', 'POST'])
def export_pdf():
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        parts = load_parts()
        builds = load_builds()
        selected_builds = request.form.getlist('builds') if request.method == 'POST' else []
        selected_parts = request.form.getlist('parts') if request.method == 'POST' else []

        filename = os.path.normpath(os.path.join(app.config['UPLOAD_FOLDER'], "part_summary.pdf"))

        doc = SimpleDocTemplate(filename, pagesize=letter, leftMargin=0.5*inch, rightMargin=0.5*inch, topMargin=0.75*inch, bottomMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        title_style.fontSize = 12
        title_style.spaceAfter = 12
        subheading_style = styles['Heading2']
        subheading_style.spaceAfter = 8

        wrapped_style = ParagraphStyle('wrapped', fontName='Helvetica', fontSize=8, leading=10)

        def build_table(data_rows):
            table = Table(data_rows, colWidths=[70, 220, 20, 70, 160])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 8),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E0E0E0')),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            return table

        if selected_builds:
            elements.append(Paragraph("Water Spider - Selected Builds Summary", title_style))
            grouped_builds = {}
            for build_id in selected_builds:
                build = builds.get(build_id, {})
                build_name = build.get('name', 'Unknown')
                if build_name not in grouped_builds:
                    grouped_builds[build_name] = []
                grouped_builds[build_name].append({'build_id': build_id, 'parts': build.get('parts', [])})

            for build_name, build_list in grouped_builds.items():
                elements.append(Paragraph(f"Build: {build_name}", subheading_style))
                for idx, build in enumerate(build_list, 1):
                    elements.append(Paragraph(f"Variant {idx}", styles['Heading3']))
                    data = [['Part Number', 'Description', 'Loc', 'Length x Width', 'Comments']]
                    for pn in build['parts']:
                        part = parts.get(pn, {})
                        data.append([
                            Paragraph(pn, wrapped_style),
                            Paragraph(part.get('description', 'N/A'), wrapped_style),
                            Paragraph(part.get('location', 'N/A'), wrapped_style),
                            Paragraph(f"{part.get('length', 'N/A')} in x {part.get('width', 'N/A')} in", wrapped_style),
                            Paragraph(part.get('comments', 'N/A'), wrapped_style)
                        ])
                    elements.append(build_table(data))
        elif selected_parts:
            elements.append(Paragraph("Water Spider - Selected Parts Summary", title_style))
            data = [['Part Number', 'Description', 'Loc', 'Dimensions', 'Comments']]
            for pn in selected_parts:
                part = parts.get(pn, {})
                data.append([
                    Paragraph(pn, wrapped_style),
                    Paragraph(part.get('description', 'N/A'), wrapped_style),
                    Paragraph(part.get('location', 'N/A'), wrapped_style),
                    Paragraph(f"{part.get('length', 'N/A')} x {part.get('width', 'N/A')} in", wrapped_style),
                    Paragraph(part.get('comments', 'N/A'), wrapped_style)
                ])
            elements.append(build_table(data))
        else:
            elements.append(Paragraph("Water Spider - All Parts Summary", title_style))
            data = [['Part Number', 'Description', 'Loc', 'Dimensions', 'Comments']]
            for pn, part in parts.items():
                data.append([
                    Paragraph(pn, wrapped_style),
                    Paragraph(part.get('description', 'N/A'), wrapped_style),
                    Paragraph(part.get('location', 'N/A'), wrapped_style),
                    Paragraph(f"{part.get('length', 'N/A')} x {part.get('width', 'N/A')} in", wrapped_style),
                    Paragraph(part.get('comments', 'N/A'), wrapped_style)
                ])
            elements.append(build_table(data))

        doc.build(elements)
        time.sleep(0.5)
        if not os.path.exists(filename):
            return f"Error: PDF file was not created at {filename}", 500
        return send_file(filename, as_attachment=True)
    except Exception as e:
        print(f"Error in export_pdf: {str(e)}")
        return f"Error generating PDF: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)

