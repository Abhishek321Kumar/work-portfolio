
<?php

include "process1.php";
session_start();


?>


<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Our Website</title>
   <style>
      <?php include 'css/style.css'; ?>
   </style>
</head>
<body>
    <section id="navbar">
     <div class="container">
 
      <nav>
        <div class="logo">
            <img src="images/grlogo2.svg" alt="logo">
   
         </div>
       
       <ul id="navmenu">
           <li><a href="http://localhost/major%20project/index.php">Home</a> </li>
           <li><a href="http://localhost/major%20project/aboutus.php">About Us</a> </li>
           <li><a href="http://localhost/major%20project/privacypolicy.php">Privacy Policy</a>  </li>
           <?php if(!isset($_SESSION['email']))
           {?>
           <li> <a href="http://localhost/major%20project/contact.php"> Contact Us</a> </li>
          <?php } ?>  
      
           
       </ul>
 


      </nav>        
     


     </div>



    </section>


    <section id="homeimg">

  <div class="container">
<div class="design">
<div class="transtruck">
<img src="images/truck1.png" alt="truck">


</div>


</div>

<div class="intro">
<h1>Welcome to <span>Green</span>Recyclers!</h1>
<p>RRR which stands for Reduce, Recycle and Reuse. Here at Green Recyclers,
   we aim at reducing the hazardous e-waste by recycling it in order to keep our environment
    clean by reusing it. We stand out from the crowd as we believe in 2 mantras: customer satisfaction and save nature. 
    We provide our customers door pick 
  up service for their e-waste. We are a growing family with many satisfied customers.</p>


</div>




  </div>


    

    

  
   

      
        



    </section>



    <section id="services">

      
   <div class="container">

      <div class="services">

          <div class="box">
            <center> <img src="images/garb1.jpg" alt="garbage man"> </center>
            <p><i>We at Green Recyclers believe in our customers satisfaction. We do so by providing door
               pick up services for picking e-waste which need to be recycled. To give item for recycling, 
               our customers need to make an account on our website and then provide their personal details 
               so that our delivery partner can pickup items from their home. 
              Customer need not to step outside from their home. We provide pick services at our customer’s ease.</i></p>
            

          </div>
          <div class="box">
            <center> <img src="images/garb2.jpg" alt="garbage man"> </center>
            <p><i>We not only do our best for the environment but we also encourage recycling and cleaning concepts in society. 
              We keep organizing “Youth Campaigns” to spread awareness about recycling among youth. 
              We visit schools/colleges to gather youth and perform cleaning the parks and also conduct campaigns.</i></p>
            


          </div>
          <div class="box">
                <center>  <img src="images/garb3.jpg" alt="garbage man"></center> 

            <p><i>A successful organization can run successfully when the employees of the company are satisfied. 
              We have employees who work day and night to run our organization in a smooth manner. We provide our 
              employees with protective helmets and specialized uniform for their protection from e-wastes.
               We follow all SOP’s regarding the Coronavirus Pandemic so that our employees and customers stay safe.</i></p>
            


          </div>





      </div>





   </div>

         
   
            

    

    </section>

    <section id="testimonials">
      <h1>Creator Portfolio</h1>
         <div class="container">

            <div class="review">

                
              <div >
                <img src="images/person1.jpg" alt="reviewer">
                <p>“I am very particular about environment from my childhood. My life got changed when my small brother 
                  got admitted to hospital after his very old mobile blasted one day. He informed me about his old phone that it’s not
                   working well. I does not paid attention as I didn’t had money to buy a new phone for him. But personally, I didn’t want to
                    dispose that mobile phone because I don’t know how to dispose it properly without harming environment. But my brother paid price 
                    of my negligence. After this incident I
                   started gathering information about recycling e-waste and that’s how this venture came in light.”
                 
                    <span><i>-Aashish</i></span>
                  
                                </p>
                    


              </div>

              <div >
                <img src="images/person2.jpg" alt="reviewer">
                <p>“I started this venture when I decided to make a change in my own lifestyle.
                  I used to dispose my old electronics without recycling it. One of my relative informed me 
                  that it can be toxic to soil, harmful to animals and environment. In addition to that, I read many 
                  articles regarding how these disposed electronic can prove to be useful when recycled and from that day I realised, like me, 
                  there are a lot of people who don’t know about recycling e-waste. So that’s how I started my Green Recyclers project”.
                  
                    <span><i>-Abhishek Anil Kumar</i></span>
                  </p>



            </div>

           





            </div>


         </div>


    </section>

    <section id="footer" class="footer">
        <div class="heading2">
         <h2> QuickLinks</h2>
        </div> 
         
         
         <div class="container">
           
            <div class="quicklinks">
   
                <ul>
   
                 <li><a href="http://localhost/major%20project/aboutus.php"> About Us</a></li>
                </ul>
   
                <?php if(!isset($_SESSION['email']))
                  {   ?>
                <ul>
                <li> <a href="http://localhost/major%20project/contact.php"> Contact Us</a> </li>
       
                </ul>
                <?php } ?> 
   
   
                <ul>
   
                 <li><a href="http://localhost/major%20project/privacypolicy.php"> Privacy Policy</a></li>
                </ul>
   
   
                <ul>
   
                 <li><a href="sale/wanttobuy.php"> Want to Buy?</a></li>
                </ul>
   
   
                </div>
            </div>
   
        
   
     <div class="footlogo">
   
   <img src="images/grlogo2.svg" alt="logo">
     </div>
       </section>
<?php 


include "user module/activesession.php "; ?>
</body>
</html>