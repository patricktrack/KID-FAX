#!/usr/bin/env python3
"""
Ticket Printing API for Raspberry Pi
This API connects to the physical printer and should be hosted on the device with the printer.
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from kidfax.printer import get_printer, print_ticket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend on different domain

@app.route('/submit_ticket', methods=['POST'])
def submit_ticket():
    """Handle ticket submission"""
    try:
        data = request.json
        from_name = data.get('from_name', 'Anonymous')
        question = data.get('question', '')
        
        if not question.strip():
            return jsonify({'success': False, 'error': 'Question/Comment cannot be empty'}), 400
        
        printer = get_printer()
        
        if printer is None:
            return jsonify({'success': False, 'error': 'Printer not available'}), 500
        
        success = print_ticket(printer, from_name, question)
        
        if success:
            logger.info(f"Ticket printed successfully from: {from_name}")
            return jsonify({'success': True, 'message': 'Ticket printed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to print ticket'}), 500
            
    except Exception as e:
        logger.error(f"Error processing ticket submission: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        printer = get_printer()
        printer_status = printer is not None
        return jsonify({
            'status': 'healthy',
            'printer_connected': printer_status
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
