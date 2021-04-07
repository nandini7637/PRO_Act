from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import OTPModel
from datetime import datetime
from django.contrib.auth import logout, authenticate, login
from django.contrib import messages
from home.models import Project_add
from random import randint
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
import json
import re

from django.contrib.auth.decorators import login_required
from .forms import ProfileUpdateForm,UserUpdateForm

from django.shortcuts import render

from bokeh.plotting import figure,output_file,show
from bokeh.embed import components 

from pandas import DataFrame
from bokeh.io import show
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource
from bokeh.palettes import Viridis9,Viridis3





# Create your views here.

def index(request):
    if request.user.is_anonymous:
        return redirect("/login")

    labels = []
    data = []
    now = datetime.now()
    queryset = Project_add.objects.all()
    
    lstProj=queryset[len(queryset)-1]
    for proj in queryset:
        labels.append(proj.name)
        dateStr=proj.date.split(' ')[0].split('-')[1]
        curYear=proj.date.split(' ')[0].split('-')[0]
        if curYear==str(now.year):
            if dateStr[0]=='0':
                data.append(dateStr[1])
            else:
                data.append(dateStr)



    df = DataFrame({
                    'month':data ,
                    })

    df2 = DataFrame({'count': df.groupby(["month"]).size()}).reset_index()
    
    df2['class-date'] = df2['month'].map(str)

    # x (months) and y(count of projects) axes
    class_date = df2['class-date'].tolist()
    count = df2['count'].tolist()

    for i in range (1,13):
        if not(str(i) in class_date):
            class_date.insert(i-1,str(i))
            count.insert(i-1,0)


    replacements = {
    '1': 'Jan',
    '2': 'Feb',
    '3': 'Mar',
    '4':'Apr',
    '5':'May',
    '6':'Jun',
    '7':'Jul',
    '8':'Aug',
    '9':'Sep',
    '10':'Oct',
    '11':'Nov',
    '12':'Dec'
    }

    class_date = [replacements.get(x, x) for x in class_date]
    monDict=dict()
    counts=[]
    for idx,c in enumerate(count):
        if c !=0:
            monDict[class_date[idx]]=[]
            counts.append(c)
        
    startIdx=0
    for idx,item in enumerate(monDict.keys()):
        print(item,monDict[item],labels[startIdx:startIdx+counts[idx]])
        monDict[item]=labels[startIdx:startIdx+counts[idx]]
        startIdx+=counts[idx]

    # Bokeh's mapping of column names and data lists 
    source = ColumnDataSource(data=dict(class_date=class_date, count=count, color=Viridis3+Viridis9))

    # Bokeh's convenience function for creating a Figure object
    p = figure(x_range=class_date, plot_height=350, title="# Projects created per month in "+str(now.year),
            toolbar_location="below")

    # Render and show the vbar plot
    p.vbar(x='class_date', top='count', width=0.9, color='color', source=source)
    script, div=components(p)

    return render(request,'index.html',{'script':script,'div':div,'lstProj':lstProj,'monDict':monDict})


def loginUser(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            if not request.POST.get('remember', None):
                request.session.set_expiry(0)
            login(request, user)
            return redirect("/")
        else:
            return render(request, 'login.html', {'error': 'Invalid Login Credentials'})
    return render(request, 'login.html')


def logoutUser(request):
    logout(request)
    return redirect('/login')


def find_email(request):
    data = json.loads(request.body)
    email = data['email']
    if not User.objects.filter(email=email).exists():
        return JsonResponse({'email_error': 'You are not registered. Please signup to continue.'}, status=404)
    return JsonResponse({'email_valid': True})


def gen_otp():
    return randint(100000, 999999)


def send_otp(request):
    user_email = request.GET['email']
    user = User.objects.get(email=user_email)
    user_name = user.first_name
    otp = gen_otp()     # Generate OTP
    # Save OTP in database and send email to user
    try:
        OTPModel.objects.create(user=user_email, otp=otp)
        data = {
            'receiver': user_name.capitalize(),
            'otp': otp
        }
        html_content = render_to_string("emails/otp.html", data)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            f"One Time Password | PRO ACT",
            text_content,
            "PRO ACT <no-reply@pro_act.com>",
            [user_email]
        )
        print("sending email")
        email.attach_alternative(html_content, "text/html")
        email.send()
        print("Sent")
        return JsonResponse({'otp_sent': f'An OTP has been sent to {user_email}.'})
    except Exception as e:
        print(e)
        return JsonResponse({'otp_error': 'Error while sending OTP, try again'})


def match_otp(email, otp):
    otp_from_db = OTPModel.objects.filter(user=email).last().otp
    return str(otp) == str(otp_from_db)

def check_otp(request):
    req_otp = request.GET['otp']
    req_user = request.GET['email']
    if match_otp(req_user, req_otp):
        return JsonResponse({'otp_match': True})
    return JsonResponse({'otp_mismatch': 'OTP does not match.'})


def password_validation(request):
    data = json.loads(request.body)
    try:
        password1 = data['password1']
    except Exception:
        password1 = data['password']
    pattern = '^(?=.*[0-9])(?=.*[a-z])(?=.*[A-Z])(?=.*[@#$%&_])(?=\S+$).{8,20}$'
    if bool(re.match(pattern, password1)):
        return JsonResponse({'password_valid': True})
    else:
        return JsonResponse({'password_error': 'Password must be 8-20 characters long and must contain atleast one uppercase letter, one lowercase letter, one number(0-9) and one special character(@,#,$,%,&,_)'})


def forgot_password(request):
    if request.method == "POST":
        try:
            password = request.POST.get('password')
            email = request.POST.get('email')
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
            return render(request, "login.html", {"message": "Password changed successfully. You can now login with your new password."})
        except Exception:
            return render(request, "forgot-password.html", {"error": "Password could not be changed, please try again."})
    return render(request, "forgot-password.html")


def project_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('desc')
        link = request.POST.get('link')
        stack = request.POST.getlist('stack')
        project_add = Project_add(
            name=name, desc=desc, link=link, stack=stack, date=datetime.today())
        project_add.save()
        messages.success(request, 'Your Project has been added')

    return render(request, 'project_add.html')


def project_view(request):
    obj = Project_add.objects.all
    return render(request, 'project_view.html', {'object': obj})

@login_required
def profile(request):
    if request.user.is_anonymous:
        return redirect("/login")
    return render(request,'profile.html')


def profile_update(request):
    if request.method=="POST":
        u_form=UserUpdateForm(request.POST,request.FILES,instance=request.user)
        p_form=ProfileUpdateForm(request.POST,request.FILES,instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request,f'You account has been updated.')
            return redirect('profile')


    else:
        u_form=UserUpdateForm(instance=request.user)
        p_form=ProfileUpdateForm(instance=request.user.profile)
        

    context={
        'u_form':u_form,
        'p_form':p_form,
    }
    return render(request,'profile_update.html',context)
