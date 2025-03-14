# pdfcompressor/views.py
from django.shortcuts import render, redirect
from django.http import FileResponse
from django.contrib.auth.decorators import login_required
import PyPDF2
from PIL import Image
import os
from django.conf import settings
import io
import traceback

def login_page(request):
    if request.user.is_authenticated:
        return redirect('compressor')
    return render(request, 'login.html')

@login_required(login_url='/login/')
def compressor(request):
    if request.method == 'POST':
        pdf_file = request.FILES.get('pdf_file')
        compression_level = request.POST.get('compression_level')
        
        if not pdf_file:
            return render(request, 'compressor.html', {'error': 'No file uploaded'})

        try:
            # Ensure media directory exists
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            
            # Sanitize filename
            safe_filename = pdf_file.name.replace(" ", "_")
            input_path = os.path.join(settings.MEDIA_ROOT, safe_filename)
            
            # Save uploaded file
            with open(input_path, 'wb+') as destination:
                for chunk in pdf_file.chunks():
                    destination.write(chunk)
            
            # Verify file exists
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"File not found after saving: {input_path}")
            
            # Compress PDF
            output_filename = f"compressed_{safe_filename}"
            output_path = os.path.join(settings.MEDIA_ROOT, output_filename)
            
            compression_rates = {
                'extreme': {'quality': 20, 'scale': 0.5},  # Low quality, 50% scale
                'recommended': {'quality': 60, 'scale': 0.75},  # Good quality, 75% scale
                'less': {'quality': 90, 'scale': 0.9}  # High quality, 90% scale
            }
            
            # Open and process the PDF
            pdf_reader = PyPDF2.PdfReader(input_path)
            pdf_writer = PyPDF2.PdfWriter()
            
            has_images = False
            original_size = os.path.getsize(input_path)
            
            for page_num, page in enumerate(pdf_reader.pages):
                # Compress images if present
                if hasattr(page, 'images') and page.images:
                    has_images = True
                    for img in page.images:
                        try:
                            # Extract image data
                            img_data = io.BytesIO(img.data)
                            pil_img = Image.open(img_data)
                            
                            # Convert to RGB if needed (PDFs often use CMYK)
                            if pil_img.mode == 'CMYK':
                                pil_img = pil_img.convert('RGB')
                            
                            # Resize image based on compression level
                            scale = compression_rates[compression_level]['scale']
                            new_size = (int(pil_img.width * scale), int(pil_img.height * scale))
                            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                            
                            # Save with specified quality
                            output_buffer = io.BytesIO()
                            pil_img.save(output_buffer, format='JPEG', quality=compression_rates[compression_level]['quality'], optimize=True)
                            img.data = output_buffer.getvalue()
                            output_buffer.close()
                        except Exception as img_error:
                            print(f"Image compression error on page {page_num}: {img_error}")
                
                # Optimize page resources (remove duplicates, compress streams)
                page.compress_content_streams()
                pdf_writer.add_page(page)
            
            # Write the compressed PDF
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            # Verify compression
            compressed_size = os.path.getsize(output_path)
            if compressed_size >= original_size and has_images:
                print(f"Warning: Compression didn’t reduce size (Original: {original_size}, Compressed: {compressed_size})")
            
            return render(request, 'compressor.html', {
                'compressed_file': output_filename,
                'original_file': safe_filename,
                'original_size': original_size // 1024,  # Size in KB
                'compressed_size': compressed_size // 1024,  # Size in KB
                'message': 'No images found to compress' if not has_images else None
            })
        
        except Exception as e:
            print(f"Error: {str(e)}")
            print(traceback.format_exc())
            return render(request, 'compressor.html', {
                'error': f"Failed to process file: {str(e)}"
            })
    
    return render(request, 'compressor.html')

@login_required
def download_file(request, filename):
    file_path = os.path.join(settings.MEDIA_ROOT, filename)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True)
    return redirect('compressor')

def logout(request):
    return redirect('login')